import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def verify_application_consistency(
    resume_data: dict,
    cover_letter_text: str,
    screening_answers: list,
    profile_data: dict,
    job_data: dict = None,
) -> dict:
    checks = {}
    warnings = []
    blockers = []
    contradictions = []

    checks = _check_resume_consistency(resume_data, profile_data)
    if not checks.get('resume_valid', True):
        blockers.append("Resume data is invalid or incomplete")
    if checks.get('warnings'):
        warnings.extend(checks.get('warnings', []))
    if checks.get('contradictions'):
        contradictions.extend(checks['contradictions'])

    cl_checks = _check_cover_letter_consistency(cover_letter_text, resume_data, profile_data, job_data)
    if cl_checks.get('contradictions'):
        warnings.extend(cl_checks['contradictions'])
        contradictions.extend(cl_checks['contradictions'])

    answer_checks = _check_screening_answer_consistency(screening_answers, resume_data, profile_data)
    if answer_checks.get('contradictions'):
        warnings.extend(answer_checks['contradictions'])
        contradictions.extend(answer_checks['contradictions'])

    profile_checks = _check_profile_completeness(profile_data, resume_data)
    if profile_checks.get('warnings'):
        warnings.extend(profile_checks['warnings'])
    if profile_checks.get('blockers'):
        blockers.extend(profile_checks['blockers'])

    if job_data:
        job_checks = _check_job_consistency(profile_data, job_data)
        if job_checks.get('warnings'):
            warnings.extend(job_checks['warnings'])
        if job_checks.get('blockers'):
            blockers.extend(job_checks['blockers'])

    is_consistent = len(contradictions) == 0
    can_submit = len(blockers) == 0

    return {
        "is_consistent": is_consistent,
        "can_submit": can_submit,
        "contradictions": contradictions,
        "warnings": warnings,
        "blockers": blockers,
        "checks_passed": {
            "resume_valid": checks.get('resume_valid', True),
            "cover_letter_consistent": cl_checks.get('consistent', True),
            "answers_consistent": answer_checks.get('consistent', True),
            "profile_complete": profile_checks.get('complete', True),
            "job_aligned": job_checks.get('aligned', True) if job_data else True,
        },
    }


def _check_resume_consistency(resume_data: dict, profile_data: dict) -> dict:
    result = {'resume_valid': True, 'warnings': [], 'contradictions': []}
    if not resume_data:
        result['resume_valid'] = False
        result['warnings'].append("No resume data provided")
        return result

    experience = resume_data.get('experience', [])
    if not experience:
        result['warnings'].append("Resume has no experience entries")

    years_exp = resume_data.get('years_of_experience', 0)
    if years_exp and experience:
        computed_years = _compute_years_from_experience(experience)
        if computed_years and abs(float(years_exp) - computed_years) > 3:
            result['contradictions'].append(
                f"Resume states {years_exp} years of experience but experience entries "
                f"suggest ~{computed_years} years"
            )

    skills = resume_data.get('skills', [])
    if not skills:
        result['warnings'].append("Resume has no skills listed")

    return result


def _check_cover_letter_consistency(
    cover_letter_text: str,
    resume_data: dict,
    profile_data: dict,
    job_data: dict = None,
) -> dict:
    result = {'consistent': True, 'contradictions': []}
    if not cover_letter_text or len(cover_letter_text) < 50:
        result['consistent'] = False
        result['contradictions'].append("Cover letter is empty or too short")
        return result

    cl_lower = cover_letter_text.lower()

    if job_data:
        company = (job_data.get('company') or '').lower()
        title = (job_data.get('title') or '').lower()
        if company and company not in cl_lower:
            result['contradictions'].append(
                f"Cover letter does not mention the target company '{job_data.get('company')}'"
            )
        if title and title not in cl_lower:
            result['contradictions'].append(
                f"Cover letter does not reference the target role '{job_data.get('title')}'"
            )

    resume_summary = (resume_data.get('summary') or '').lower()
    if resume_summary:
        key_terms = set(re.findall(r'\b[a-z]{4,}\b', resume_summary))
        cl_terms = set(re.findall(r'\b[a-z]{4,}\b', cl_lower))
        overlap = key_terms & cl_terms
        if len(overlap) < 2 and len(key_terms) > 5:
            result['contradictions'].append(
                "Cover letter does not reference any specific terms from the resume summary"
            )

    skills = resume_data.get('skills', [])
    if skills:
        matched_skills = [s for s in skills if s.lower() in cl_lower]
        if not matched_skills:
            result['contradictions'].append(
                "Cover letter does not mention any skills from the candidate's resume"
            )

    return result


def _check_screening_answer_consistency(
    screening_answers: list,
    resume_data: dict,
    profile_data: dict,
) -> dict:
    result = {'consistent': True, 'contradictions': []}
    if not screening_answers:
        return result

    skills = [s.lower() for s in resume_data.get('skills', [])]
    experience = resume_data.get('experience', [])
    years_exp = float(resume_data.get('years_of_experience', 0))
    education = resume_data.get('education', [])
    work_auth = (resume_data.get('work_authorization') or '').lower()
    goals = profile_data.get('goals', {})

    for ans in screening_answers:
        q = ans.get('question', '').lower()
        a = ans.get('answer', '').lower()
        confidence = ans.get('confidence', 0.5)

        if confidence < 0.3:
            result['contradictions'].append(
                f"Low confidence answer ({confidence}) for: '{ans.get('question', '')[:60]}'"
            )

        if 'years' in q and ('experience' in q or 'work' in q):
            years_in_answer = _extract_years(a)
            if years_in_answer and years_exp and abs(years_in_answer - years_exp) > 2:
                result['contradictions'].append(
                    f"Answer states ~{years_in_answer} years but resume shows {years_exp}: "
                    f"'{ans.get('question', '')[:50]}'"
                )

        if 'salary' in q:
            salary_goals = {
                'min': goals.get('target_salary_min'),
                'max': goals.get('target_salary_max'),
            }
            numbers = re.findall(r'\b\d{4,6}\b', a)
            if numbers and salary_goals.get('max'):
                stated_max = max(int(n) for n in numbers)
                if stated_max > salary_goals['max'] * 1.2:
                    result['contradictions'].append(
                        f"Answer states salary ~${stated_max:,} but profile max is "
                        f"${salary_goals['max']:,}"
                    )

        if 'authorization' in q or 'visa' in q or 'sponsor' in q:
            if work_auth and work_auth not in a:
                result['contradictions'].append(
                    f"Work authorization answer doesn't match profile: '{ans.get('question', '')[:50]}'"
                )

        if 'skill' in q or 'technology' in q or any(s in q for s in ['python', 'java', 'javascript', 'react', 'aws', 'sql']):
            mentioned_skills = [s for s in skills if s in a]
            if not mentioned_skills and skills:
                pass

        if 'education' in q or 'degree' in q:
            if education:
                degrees = [str(e.get('degree', '')).lower() for e in education]
                if not any(d in a for d in degrees if d):
                    pass

        if 'location' in q or 'relocate' in q or 'remote' in q:
            preferred = goals.get('remote_preference', 'any').lower()
            if preferred != 'any':
                if preferred == 'remote' and 'remote' not in a and 'yes' in a:
                    pass

    return result


def _check_profile_completeness(profile_data: dict, resume_data: dict = None) -> dict:
    result = {'complete': True, 'warnings': [], 'blockers': []}
    if resume_data is None:
        resume_data = profile_data.get('resume', {})
    goals = profile_data.get('goals', {})

    if not resume_data:
        result['complete'] = False
        result['blockers'].append("No resume data in profile")
        return result

    if not resume_data.get('skills'):
        result['warnings'].append("No skills listed in resume")

    if not resume_data.get('experience'):
        result['warnings'].append("No experience entries in resume")

    if not resume_data.get('years_of_experience'):
        result['warnings'].append("Years of experience not specified")

    if not goals.get('target_titles'):
        result['warnings'].append("No target job titles configured")

    if not goals.get('work_authorization'):
        result['warnings'].append("Work authorization not configured")

    return result


def _check_job_consistency(profile_data: dict, job_data: dict) -> dict:
    result = {'aligned': True, 'warnings': [], 'blockers': []}
    resume_data = profile_data.get('resume', {})
    goals = profile_data.get('goals', {})

    job_location = (job_data.get('location') or '').lower()
    preferred_locations = [l.lower() for l in goals.get('target_locations', [])]
    remote_pref = goals.get('remote_preference', 'any').lower()

    if job_location and preferred_locations:
        if remote_pref == 'remote' and 'remote' not in job_location:
            result['warnings'].append(
                f"Job is in {job_location} but candidate prefers remote"
            )

    job_salary_min = job_data.get('salary_min') or 0
    job_salary_max = job_data.get('salary_max') or 0
    target_salary_min = goals.get('target_salary_min') or 0
    target_salary_max = goals.get('target_salary_max') or 0

    if target_salary_min and job_salary_max:
        if job_salary_max < target_salary_min * 0.8:
            result['warnings'].append(
                f"Job salary max (${job_salary_max}) is below candidate minimum "
                f"(${target_salary_min})"
            )

    job_skills = [r.lower() for r in job_data.get('requirements', [])]
    candidate_skills = [s.lower() for s in resume_data.get('skills', [])]

    if job_skills and candidate_skills:
        missing = [s for s in job_skills if s not in candidate_skills]
        if len(missing) > len(job_skills) * 0.5:
            result['warnings'].append(
                f"Candidate missing {len(missing)}/{len(job_skills)} required skills"
            )

    return result


def _compute_years_from_experience(experience: list) -> Optional[float]:
    total_days = 0
    for exp in experience:
        start = exp.get('start_date', '')
        end = exp.get('end_date', '') or 'Present'
        try:
            if end.lower() == 'present':
                end_date = datetime.now()
            else:
                end_date = _parse_date(end)
            start_date = _parse_date(start)
            if start_date and end_date:
                total_days += (end_date - start_date).days
        except Exception:
            continue
    return round(total_days / 365.25, 1) if total_days else None


def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%d', '%Y-%m', '%Y',
        '%m/%Y', '%m/%d/%Y',
        '%B %Y', '%B %d, %Y',
        '%b %Y', '%b %d, %Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime(int(date_str[:4]), 1, 1)
    except Exception:
        return None


def _extract_years(text: str) -> Optional[float]:
    numbers = re.findall(r'(\d+)\+?\s*(?:year|yr)s?', text)
    if numbers:
        return float(numbers[0])
    numbers = re.findall(r'(\d+)\+?\s*(?:year|yr)s?\s+(?:of\s+)?experience', text)
    if numbers:
        return float(numbers[0])
    return None
