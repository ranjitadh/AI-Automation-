import json
import logging
from typing import Optional

from .gateway import generate
from .schemas import RESUME_ADAPTATION_SCHEMA

logger = logging.getLogger(__name__)


def adapt_resume(resume_data: dict, job_data: dict, calibration: dict = None,
                 organization_id: str = None, user_id: str = None) -> dict:
    system_prompt = (
        "You are an expert ATS resume adaptation specialist. Your job is to tailor "
        "a candidate's resume for a specific job application. "
        "CRITICAL RULES - YOU MUST FOLLOW THESE: "
        "1. NEVER invent jobs, degrees, certifications, companies, or dates. "
        "2. NEVER fabricate experience. All information must be truthful. "
        "3. You MAY reorder experience entries to put most relevant first. "
        "4. You MAY rewrite bullet points to emphasize relevant technologies and achievements. "
        "5. You MAY improve wording for ATS compatibility and readability. "
        "6. You MAY adjust skill emphasis based on calibration guidance. "
        "7. If calibration says 'downgrade', reduce emphasis on leadership/executive roles. "
        "8. If calibration says 'upgrade', highlight transferable skills and adjacent technologies. "
        "9. The resume should appear naturally optimized, never keyword-stuffed. "
        "10. Avoid generic AI language, buzzword overload, and robotic phrasing. "
        "Output a JSON with adapted_summary, adapted_experience (array with company, title, "
        "start_date, end_date, bullets), adapted_skills, skill_emphasis, "
        "seniority_presentation, and changes_summary."
    )

    calibration_info = calibration or {
        "calibration_type": "maintain",
        "seniority_gap": "match",
        "changes": {},
    }

    user_prompt = json.dumps({
        "resume": resume_data,
        "job": job_data,
        "calibration": calibration_info,
        "instructions": (
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

    return adapted


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
        metadata={'truthfulness_verified': truthfulness_verified},
    )

    ResumeVersion.objects.filter(resume=resume, is_active=True).exclude(id=version.id).update(is_active=False)

    return version
