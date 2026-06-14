import json
import logging
import tiktoken
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from django.conf import settings
from apps.analysis.usage_tracker import check_daily_budget, log_usage

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    max_retries=3,
    timeout=30.0,
) if settings.OPENAI_API_KEY else None

def _count_tokens(text, model="gpt-4o"):
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return len(text.split())

def _call_gpt(system_prompt, user_prompt, response_format=None):
    if not client:
        logger.warning("OpenAI API key not configured")
        return {}
    if not check_daily_budget():
        logger.error("Daily OpenAI budget exceeded")
        return {} if response_format else ""
    try:
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.OPENAI_TEMPERATURE,
            "max_tokens": settings.OPENAI_MAX_TOKENS,
        }
        if response_format:
            kwargs["response_format"] = response_format
        r = client.chat.completions.create(**kwargs)
        content = r.choices[0].message.content
        input_tokens = _count_tokens(system_prompt + user_prompt)
        output_tokens = _count_tokens(content or "")
        log_usage(
            model=settings.OPENAI_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            endpoint="chat.completions",
        )
        if response_format:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OpenAI response as JSON: {content[:200]}")
                return {}
        return content
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {e}")
        return {} if response_format else ""
    except APITimeoutError as e:
        logger.error(f"OpenAI request timed out: {e}")
        return {} if response_format else ""
    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return {} if response_format else ""
    except Exception as e:
        logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
        return {} if response_format else ""

def get_embedding(text):
    if not client:
        return None
    if not check_daily_budget():
        logger.error("Daily OpenAI budget exceeded")
        return None
    try:
        r = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000],
        )
        log_usage(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input_tokens=_count_tokens(text[:8000]),
            output_tokens=0,
            endpoint="embeddings.create",
        )
        return r.data[0].embedding
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded (embedding): {e}")
        return None
    except APITimeoutError as e:
        logger.error(f"OpenAI embedding request timed out: {e}")
        return None
    except APIError as e:
        logger.error(f"OpenAI embedding API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected embedding error: {e}", exc_info=True)
        return None

def analyze_job_fit(job, resume=None):
    system = """You are a senior technical recruiter and career coach. Analyze this job posting against the candidate's resume.

Return JSON:
{
  "fit_score": 0-100,
  "ats_score": 0-100,
  "experience_score": 0-100,
  "skill_match_score": 0-100,
  "keyword_score": 0-100,
  "location_score": 0-100,
  "salary_score": 0-100,
  "education_score": 0-100,
  "seniority_score": 0-100,
  "overall_score": 0-100,
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "years_experience_required": 5,
  "seniority_level": "Senior",
  "education_required": "Bachelor's",
  "technologies": ["tech1", "tech2"],
  "keywords": ["keyword1", "keyword2"],
  "skill_gaps": [{"skill": "Kubernetes", "importance": "high", "has": false}],
  "experience_gaps": ["No management experience"],
  "keyword_gaps": ["CI/CD", "Terraform"],
  "strengths": ["Strong in Python", "10+ years experience"],
  "weaknesses": ["No cloud certification"],
  "recommendations": ["Add Kubernetes to resume", "Highlight Python projects"],
  "recommendation": "strong_apply|apply|consider|skip",
  "salary_range": {"min": 100000, "max": 150000, "currency": "USD"}
}"""

    resume_text = ""
    if resume:
        resume_text = f"""
Resume:
Title: {resume.title}
Summary: {resume.summary or 'N/A'}
Skills: {', '.join(s.get('name', '') for s in (resume.skills or []))}
Experience: {json.dumps(resume.experience or [])}
Education: {json.dumps(resume.education or [])}
Years Exp: {resume.years_of_experience or 'N/A'}
"""

    prompt = f"""
Job Title: {job.title}
Company: {job.company.name}
Location: {job.location or 'N/A'}
Seniority: {job.seniority or 'N/A'}
Employment Type: {job.employment_type or 'N/A'}
Salary: {job.salary_min or 'N/A'} - {job.salary_max or 'N/A'} {job.salary_currency or 'USD'}
Remote: {'Yes' if job.remote else 'No' if job.remote is False else 'Unknown'}

Description:
{job.description or 'N/A'}

Requirements:
{json.dumps(job.requirements or [])}

Responsibilities:
{json.dumps(job.responsibilities or [])}

Nice to Have:
{json.dumps(job.nice_to_have or [])}

{resume_text}

Analyze this job posting and provide a complete fit analysis with all scores.
"""

    result = _call_gpt(system, prompt, {"type": "json_object"})
    return result

def analyze_ats(job, resume):
    system = """You are an ATS (Applicant Tracking System) expert. Analyze how well this resume matches the job posting for ATS compatibility.

Return JSON:
{
  "ats_score": 0-100,
  "keyword_match_rate": 0.0-100.0,
  "formatting_score": 0-100,
  "section_score": 0-100,
  "missing_sections": ["section1"],
  "missing_keywords": ["keyword1"],
  "suggested_improvements": ["improvement1"],
  "optimized_sections": {"summary": "optimized text"}
}"""

    prompt = f"""
Job Title: {job.title}
Description: {job.description or 'N/A'}
Requirements: {json.dumps(job.requirements or [])}

Resume Title: {resume.title}
Resume Text: {resume.parsed_text or ''}
Skills: {json.dumps(resume.skills or [])}

Analyze ATS compatibility and provide optimization suggestions.
"""
    return _call_gpt(system, prompt, {"type": "json_object"})

def optimize_resume(resume, job=None):
    system = """You are a professional resume writer and ATS optimization expert. Optimize the resume for the target job.

Return JSON:
{
  "optimized_text": "Full optimized resume text",
  "changes": {"summary": "Added keywords", "skills": ["Kubernetes"], "experience": "Rephrased"},
  "ats_score": 85
}"""

    job_context = ""
    if job:
        job_context = f"""
Target Job: {job.title}
Company: {job.company.name}
Description: {job.description or 'N/A'}
Requirements: {json.dumps(job.requirements or [])}
"""

    prompt = f"""
{job_context}
Resume Title: {resume.title}
Current Text: {resume.parsed_text or ''}
Skills: {json.dumps(resume.skills or [])}
Experience: {json.dumps(resume.experience or [])}

Optimize this resume for ATS compatibility and job matching.
"""
    return _call_gpt(system, prompt, {"type": "json_object"})
