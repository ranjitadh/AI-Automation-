import json
import logging
import re
from typing import Optional

from .gateway import generate
from .schemas import RESUME_ADAPTATION_SCHEMA

logger = logging.getLogger(__name__)


ROLE_CATEGORIES = {
    "ai_ml": {"keywords": ["machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch", "llm", "ai", "data science", "neural network"]},
    "backend": {"keywords": ["backend", "api", "microservice", "rest", "graphql", "server", "database", "distributed system", "python", "java", "go", "rust"]},
    "frontend": {"keywords": ["frontend", "react", "angular", "vue", "ui", "css", "javascript", "typescript", "web"]},
    "data": {"keywords": ["data engineer", "data analyst", "data science", "etl", "pipeline", "big data", "spark", "sql", "warehouse"]},
    "devops": {"keywords": ["devops", "ci/cd", "kubernetes", "docker", "infrastructure", "terraform", "aws", "gcp", "azure", "deployment"]},
    "product": {"keywords": ["product manager", "product owner", "strategy", "roadmap", "stakeholder", "agile"]},
}

INDUSTRY_CATEGORIES = {
    "fintech": {"keywords": ["fintech", "finance", "banking", "payment", "trading", "blockchain"]},
    "healthcare": {"keywords": ["healthcare", "health", "medical", "biotech", "pharma", "clinical"]},
    "saas": {"keywords": ["saas", "b2b", "b2c", "subscription", "platform"]},
}

SENIORITY_LEVELS = ["junior", "mid", "senior", "lead", "principal", "staff", "manager", "director", "vp"]


def adapt_resume(resume_data: dict, job_data: dict, calibration: dict = None,
                 organization_id: str = None, user_id: str = None) -> dict:
    role_category = _detect_role_category(job_data)
    industry_category = _detect_industry_category(job_data)
    seniority = _detect_seniority(job_data)

    system_prompt = _build_adaptation_system_prompt(role_category, industry_category, seniority)

    calibration_info = calibration or {
        "calibration_type": "maintain",
        "seniority_gap": "match",
        "changes": {},
    }

    user_prompt = json.dumps({
        "resume": resume_data,
        "job": job_data,
        "calibration": calibration_info,
        "role_category": role_category,
        "industry_category": industry_category,
        "detected_seniority": seniority,
        "instructions": (
            f"Adapt this resume for a {seniority}-level {role_category} role in the {industry_category} industry. "
            "For each experience entry: keep company, title, start_date, end_date EXACTLY "
            "as they appear in the resume. Only rewrite the bullet points. "
            "If calibration_type is 'downgrade': rephrase leadership-heavy bullets "
            "to focus on technical contributions and team participation. "
            "If calibration_type is 'upgrade': emphasize relevant transferable skills "
            "and adjacent domain experience. "
            "Reorder experience so the most role-relevant entries appear first. "
            "Aim for an ATS score of 80+ while maintaining natural human readability."
        ),
    })

    result = generate(
        task_type='resume_adaptation',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=RESUME_ADAPTATION_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    adapted = result.get('parsed', result)

    if adapted and adapted.get('adapted_experience'):
        original = resume_data.get('experience', [])
        issues = verify_resume_truthfulness(original, adapted.get('adapted_experience', []))
        if issues:
            logger.warning(f"Resume truthfulness issues detected: {issues}")
            adapted['truthfulness_warnings'] = issues
            adapted['_has_fabrication'] = True
        else:
            adapted['truthfulness_verified'] = True

    adapted['role_category'] = role_category
    adapted['industry_category'] = industry_category
    adapted['seniority_presentation'] = seniority

    return adapted


def _build_adaptation_system_prompt(role: str, industry: str, seniority: str) -> str:
    role_guidance = {
        "ai_ml": "Emphasize ML/AI frameworks, model development, data pipeline experience, and quantitative achievements. Highlight specific algorithms, accuracy metrics, and production deployments.",
        "backend": "Emphasize system architecture, API design, database optimization, scalability, and reliability. Highlight specific technologies, throughput metrics, and system uptime.",
        "frontend": "Emphasize UI/UX implementation, component architecture, performance optimization, and cross-browser compatibility. Highlight specific frameworks, bundle size reductions, and accessibility improvements.",
        "data": "Emphasize ETL pipelines, data modeling, analytics, visualization, and data quality. Highlight specific tools, data volume metrics, and business impact.",
        "devops": "Emphasize infrastructure automation, CI/CD pipelines, containerization, monitoring, and incident response. Highlight uptime metrics, deployment frequency, and cost optimization.",
        "product": "Emphasize product strategy, stakeholder management, user research, and cross-functional leadership. Highlight metrics around adoption, engagement, and revenue impact.",
        "general": "Focus on transferable skills, problem-solving, and impact metrics that any technical manager would value.",
    }.get(role, "Focus on transferable skills and measurable impact.")

    industry_guidance = {
        "fintech": "Emphasize security, compliance, accuracy, and handling sensitive financial data. Highlight experience with regulated environments.",
        "healthcare": "Emphasize HIPAA compliance, patient data handling, reliability, and healthcare domain knowledge. Highlight experience with regulated data.",
        "saas": "Emphasize multi-tenant architecture, scalability, customer-facing features, and metrics-driven development. Highlight experience with subscription models.",
        "general": "Focus broadly on transferable skills and impact.",
    }.get(industry, "Focus broadly on transferable skills and impact.")

    seniority_guidance = {
        "junior": "Emphasize learning ability, growth mindset, collaboration skills, and foundational technical competence.",
        "mid": "Emphasize independent execution, technical depth, project ownership, and cross-team collaboration.",
        "senior": "Emphasize technical leadership, mentoring, architecture decisions, and driving complex projects to completion.",
        "lead": "Emphasize team leadership, technical strategy, project planning, and stakeholder communication.",
        "principal": "Emphasize organization-wide technical vision, system design, technical mentorship, and strategic impact.",
        "manager": "Emphasize people management, team building, delivery management, and engineering process improvement.",
        "director": "Emphasize organizational leadership, strategy, team scaling, and cross-department collaboration.",
    }.get(seniority, "Emphasize relevant experience at the appropriate level.")

    return (
        "You are an expert ATS resume adaptation specialist. Your job is to tailor "
        "a candidate's resume for a specific job application. "
        "CRITICAL RULES - YOU MUST FOLLOW THESE: "
        "1. NEVER invent jobs, degrees, certifications, companies, or dates. "
        "2. NEVER fabricate experience. All information must be truthful. "
        "3. You MAY reorder experience entries to put most relevant first. "
        "4. You MAY rewrite bullet points to emphasize relevant technologies and achievements. "
        "5. You MAY improve wording for ATS compatibility and readability. "
        "6. You MAY adjust skill emphasis based on calibration guidance. "
        "7. The resume should appear naturally optimized, never keyword-stuffed. "
        "8. Avoid generic AI language, buzzword overload, and robotic phrasing. "
        f"CURRENT ADAPTATION CONTEXT: Role={role}, Industry={industry}, Level={seniority}. "
        f"Role guidance: {role_guidance} "
        f"Industry guidance: {industry_guidance} "
        f"Seniority guidance: {seniority_guidance} "
        "Output a JSON with adapted_summary, adapted_experience (array with company, title, "
        "start_date, end_date, bullets), adapted_skills, skill_emphasis, "
        "seniority_presentation, and changes_summary."
    )


def _detect_role_category(job_data: dict) -> str:
    text = _get_job_text(job_data).lower()
    scores = {}
    for category, info in ROLE_CATEGORIES.items():
        score = sum(2 if kw in text else 0 for kw in info["keywords"])
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else "general"


def _detect_industry_category(job_data: dict) -> str:
    text = _get_job_text(job_data).lower()
    company = (job_data.get("company_name") or job_data.get("company") or "").lower()
    text += " " + company
    scores = {}
    for category, info in INDUSTRY_CATEGORIES.items():
        score = sum(2 if kw in text else 0 for kw in info["keywords"])
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else "general"


def _detect_seniority(job_data: dict) -> str:
    title = (job_data.get("title") or "").lower()
    seniority = (job_data.get("seniority_level") or "").lower()
    combined = title + " " + seniority

    for level in SENIORITY_LEVELS:
        if level in combined:
            return level

    years_req = job_data.get("years_experience_required", 0) or job_data.get("years_required", 0)
    if years_req:
        if years_req <= 2:
            return "junior"
        elif years_req <= 5:
            return "mid"
        elif years_req <= 8:
            return "senior"
        else:
            return "lead"

    return "mid"


def _get_job_text(job_data: dict) -> str:
    return " ".join(filter(None, [
        job_data.get("title", ""),
        job_data.get("description", ""),
        " ".join(job_data.get("required_skills", [])),
        " ".join(job_data.get("responsibilities", [])),
        " ".join(job_data.get("requirements", [])),
    ]))


def verify_resume_truthfulness(original_experience: list, adapted_experience: list) -> list:
    issues = []
    original_map = {}
    for exp in original_experience:
        key = _normalize_key(exp.get('company', ''), exp.get('title', ''))
        original_map[key] = exp

    adapted_keys = set()
    for exp in adapted_experience:
        company = exp.get('company', '')
        title = exp.get('title', '')
        start_date = exp.get('start_date', '')
        end_date = exp.get('end_date', '')

        key = _normalize_key(company, title)
        adapted_keys.add(key)

        if key not in original_map:
            issues.append(
                f"FABRICATED: '{title}' at '{company}' — not found in original resume"
            )
        else:
            orig = original_map[key]
            if start_date and orig.get('start_date'):
                orig_start = _normalize_date(orig.get('start_date', ''))
                adapted_start = _normalize_date(start_date)
                if adapted_start != orig_start and adapted_start:
                    issues.append(
                        f"DATE MISMATCH for '{title}' at '{company}': "
                        f"start_date '{start_date}' != original '{orig.get('start_date')}'"
                    )
            if end_date and orig.get('end_date') and end_date.lower() != 'present':
                orig_end = _normalize_date(orig.get('end_date', ''))
                adapted_end = _normalize_date(end_date)
                if adapted_end != orig_end and adapted_end:
                    issues.append(
                        f"DATE MISMATCH for '{title}' at '{company}': "
                        f"end_date '{end_date}' != original '{orig.get('end_date')}'"
                    )

    for orig_key in original_map:
        if orig_key not in adapted_keys:
            orig = original_map[orig_key]
            issues.append(
                f"MISSING: '{orig.get('title')}' at '{orig.get('company')}' "
                f"— experience dropped without explanation"
            )

    return issues


def _normalize_key(company: str, title: str) -> str:
    c = company.strip().lower() if company else ''
    t = title.strip().lower() if title else ''
    c = c.replace('inc', '').replace('corp', '').replace('llc', '').replace('ltd', '').strip()
    t = t.replace('sr.', 'senior').replace('jr.', 'junior').strip()
    return f"{c}|{t}"


def _normalize_date(date_str: str) -> str:
    if not date_str:
        return ''
    d = date_str.strip().lower()
    d = d.replace(',', '').replace('.', '')
    month_map = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }
    for abbr, num in month_map.items():
        d = d.replace(abbr, num)
    return d[:7]


def create_resume_version(resume, job, adapted_result: dict, organization) -> Optional[object]:
    from apps.resumes.models import ResumeVersion

    if adapted_result.get('_has_fabrication'):
        logger.error(
            f"Refusing to create resume version — fabrication detected: "
            f"{adapted_result.get('truthfulness_warnings', [])}"
        )
        return None

    adapted_experience = adapted_result.get('adapted_experience', [])
    adapted_skills = adapted_result.get('adapted_skills', [])
    adapted_summary = adapted_result.get('adapted_summary', '')
    changes_summary = adapted_result.get('changes_summary', {})
    ats_estimate = adapted_result.get('ats_score_estimate', 0)
    truthfulness_verified = adapted_result.get('truthfulness_verified', False)
    role_category = adapted_result.get('role_category', 'general')
    industry_category = adapted_result.get('industry_category', 'general')
    seniority = adapted_result.get('seniority_presentation', 'mid')

    adapted_text_parts = [adapted_summary, "", "--- Experience ---"]
    for exp in adapted_experience:
        company = exp.get('company', '')
        title = exp.get('title', '')
        dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}"
        adapted_text_parts.append(f"\n{title} at {company} ({dates})")
        for bullet in exp.get('bullets', []):
            adapted_text_parts.append(f"  - {bullet}")

    if adapted_skills:
        adapted_text_parts.append("\n--- Skills ---")
        adapted_text_parts.append(", ".join(adapted_skills))

    adapted_text = "\n".join(adapted_text_parts)

    version_number = 1
    existing = ResumeVersion.objects.filter(resume=resume).order_by('-version_number').first()
    if existing:
        version_number = existing.version_number + 1

    version = ResumeVersion.objects.create(
        resume=resume,
        version_number=version_number,
        optimized_for_job=job,
        original_text=resume.parsed_text or resume.summary or "",
        optimized_text=adapted_text,
        changes_summary=changes_summary,
        ats_score=ats_estimate,
        is_active=True,
        metadata={
            'truthfulness_verified': truthfulness_verified,
            'role_category': role_category,
            'industry_category': industry_category,
            'seniority_level': seniority,
        },
    )

    ResumeVersion.objects.filter(resume=resume, is_active=True).exclude(id=version.id).update(is_active=False)

    return version
