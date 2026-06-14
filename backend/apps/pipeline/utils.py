import json
import logging
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from django.conf import settings
from apps.analysis.usage_tracker import check_daily_budget, log_usage

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    max_retries=3,
    timeout=30.0,
) if settings.OPENAI_API_KEY else None

def _count_tokens(text):
    try:
        import tiktoken
        enc = tiktoken.encoding_for_model(settings.OPENAI_MODEL)
        return len(enc.encode(text))
    except Exception:
        return len(text.split())

def _call_gpt(system, prompt):
    if not client:
        logger.warning("OpenAI API key not configured")
        return {}
    if not check_daily_budget():
        logger.error("Daily OpenAI budget exceeded")
        return {}
    try:
        r = client.chat.completions.create(
            model=settings.OPENAI_MODEL, messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ], response_format={"type": "json_object"}
        )
        content = r.choices[0].message.content
        log_usage(
            model=settings.OPENAI_MODEL,
            input_tokens=_count_tokens(system + prompt),
            output_tokens=_count_tokens(content or ""),
            endpoint="chat.completions",
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse OpenAI response as JSON: {content[:200]}")
            return {}
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {e}")
        return {}
    except APITimeoutError as e:
        logger.error(f"OpenAI request timed out: {e}")
        return {}
    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected OpenAI error: {e}", exc_info=True)
        return {}

def analyze_job_fit(job):
    return _call_gpt(
        "You are a job fit analyst.",
        f"Job: {job.title} @ {job.company}\nLocation: {job.location or 'N/A'}\nDescription: {job.job_description_text or 'N/A'}\n\nOutput JSON: {{\"score\": 0-100, \"strengths\": [], \"gaps\": [], \"key_requirements\": []}}"
    ) or {"score": 50, "strengths": [], "gaps": [], "key_requirements": []}

def generate_cover_letter(job, resume_text="", skills=None):
    skills_text = ", ".join(skills) if skills else "N/A"
    data = _call_gpt(
        "You write concise, tailored cover letters.",
        f"""Job: {job.title} @ {job.company}\nDescription: {job.job_description_text or 'N/A'}\nResume: {resume_text or 'N/A'}\nSkills: {skills_text}\n\nRules: 150-250 words, professional, tailored, first-person, no placeholders, no AI mention.\n\nOutput JSON: {{"subject": "Application for {job.title}", "cover_letter": "..."}}"""
    ) or {}
    return {
        "subject": data.get("subject", f"Application for {job.title} at {job.company}"),
        "cover_letter": data.get("cover_letter", f"Application for {job.title} at {job.company}")
    }
