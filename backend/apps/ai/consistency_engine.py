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

    tech_checks = _check_technology_alignment(resume_data, job_data)
    if tech_checks.get('warnings'):
        warnings.extend(tech_checks['warnings'])
    if tech_checks.get('contradictions'):
        contradictions.extend(tech_checks['contradictions'])

    loc_checks = _check_location_consistency(profile_data, job_data, screening_answers)
    if loc_checks.get('contradictions'):
        contradictions.extend(loc_checks['contradictions'])

    edu_checks = _check_education_consistency(resume_data, screening_answers, job_data)
    if edu_checks.get('contradictions'):
        contradictions.extend(edu_checks['contradictions'])

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
            "technology_aligned": tech_checks.get('aligned', True),
            "location_consistent": loc_checks.get('consistent', True),
            "education_consistent": edu_checks.get('consistent', True),
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

        if 'education' in q or 'degree' in q or 'qualification' in q:
            if education:
                degrees = [str(e.get('degree', '')).lower() for e in education if e.get('degree')]
                if degrees and not any(d in a for d in degrees):
                    result['contradictions'].append(
                        f"Education answer '{ans.get('answer', '')[:50]}' doesn't match "
                        f"resume degrees: {', '.join(d[:20] for d in degrees)}"
                    )

        if 'skill' in q or 'technology' in q:
            mentioned_skills = [s for s in skills if s in a]
            if not mentioned_skills and skills:
                result['warnings'] = result.get('warnings', [])
                result['warnings'].append(
                    f"No skills from resume mentioned in answer about skills"
                )

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


SKILL_SYNONYMS = {
    "ci/cd": ["continuous integration", "continuous deployment", "ci", "cd"],
    "cicd": ["continuous integration", "continuous deployment", "ci", "cd"],
    "k8s": ["kubernetes", "k8", "kube"],
    "kubernetes": ["k8s", "k8", "kube"],
    "js": ["javascript", "ecmascript"],
    "javascript": ["js", "ecmascript"],
    "ts": ["typescript"],
    "typescript": ["ts"],
    "node.js": ["nodejs", "node", "node js"],
    "nodejs": ["node.js", "node", "node js"],
    "next.js": ["nextjs", "next", "next js"],
    "nextjs": ["next.js", "next", "next js"],
    "react.js": ["reactjs", "react", "react js"],
    "reactjs": ["react.js", "react", "react js"],
    "vue.js": ["vuejs", "vue", "vue js"],
    "vuejs": ["vue.js", "vue", "vue js"],
    "express.js": ["expressjs", "express", "express js"],
    "expressjs": ["express.js", "express", "express js"],
    "rest api": ["rest", "restful", "rest api", "restful api"],
    "rest apis": ["rest", "restful", "rest api", "restful api"],
    "restful api": ["rest", "rest api", "rest apis"],
    "graphql": ["gql", "graph ql"],
    "aws": ["amazon web services", "amazon"],
    "gcp": ["google cloud platform", "google cloud"],
    "azure": ["microsoft azure", "ms azure"],
    "aws lambda": ["lambda", "serverless function", "amazon lambda"],
    "s3": ["amazon s3", "simple storage service"],
    "sqs": ["amazon sqs", "simple queue service"],
    "docker": ["container", "containerization", "docker engine"],
    "terraform": ["iac", "infrastructure as code", "terraform cloud"],
    "postgresql": ["postgres", "postgres sql"],
    "postgres": ["postgresql", "postgres sql"],
    "pandas": ["python pandas", "dataframe", "data frames"],
    "python": ["python3", "python 3"],
    "react": ["react.js", "reactjs", "react js"],
    "vue": ["vue.js", "vuejs", "vue js"],
    "angular": ["angular.js", "angularjs", "angular 2+"],
    "redis": ["redis cache", "redis db"],
    "mongodb": ["mongo", "mongo db"],
    "mysql": ["my sql", "sql"],
    "django": ["django framework", "django python"],
    "fastapi": ["fast api", "fast-api"],
    "flask": ["flask python", "python flask"],
}


def _normalize_skills(skills: set) -> set:
    normalized = set()
    for skill in skills:
        skill_clean = skill.strip().lower()
        if skill_clean in SKILL_SYNONYMS:
            normalized.update(SKILL_SYNONYMS[skill_clean])
        normalized.add(skill_clean)
        parts = re.split(r'[/\-.+#]', skill_clean)
        for p in parts:
            p = p.strip()
            if len(p) > 1:
                normalized.add(p.lower())
    return normalized


def _check_technology_alignment(resume_data: dict, job_data: dict) -> dict:
    result = {'aligned': True, 'warnings': [], 'contradictions': []}
    if not resume_data or not job_data:
        return result

    job_technologies = set(
        t.lower() for t in (
            job_data.get('required_skills', []) +
            job_data.get('technologies', []) +
            job_data.get('tools', [])
        )
    )
    if not job_technologies:
        return result

    resume_text_parts = []
    for exp in resume_data.get('experience', []):
        resume_text_parts.append(exp.get('title', ''))
        resume_text_parts.extend(exp.get('bullets', []))

    resume_skills = set(s.lower() for s in resume_data.get('skills', []))
    resume_text = ' '.join(resume_text_parts).lower()

    all_resume_tech = resume_skills | set(re.findall(r'\b[a-z0-9+#.\-]+(?:\s+[a-z0-9+#.\-]+)*\b', resume_text))
    all_resume_tech = _normalize_skills(all_resume_tech)
    job_technologies = _normalize_skills(job_technologies)

    missing_critical = []
    for tech in job_technologies:
        if tech not in all_resume_tech:
            missing_critical.append(tech)

    if len(missing_critical) > len(job_technologies) * 0.4:
        result['aligned'] = False
        result['contradictions'].append(
            f"Candidate missing {len(missing_critical)}/{len(job_technologies)} "
            f"required technologies: {', '.join(sorted(missing_critical)[:6])}"
        )
    elif missing_critical:
        result['warnings'].append(
            f"Candidate missing technologies: {', '.join(sorted(missing_critical)[:4])}"
        )

    return result


def _check_location_consistency(profile_data: dict, job_data: dict, screening_answers: list) -> dict:
    result = {'consistent': True, 'contradictions': []}
    goals = profile_data.get('goals', {})

    if not job_data:
        return result

    job_location = (job_data.get('location') or '').lower()
    remote_pref = goals.get('remote_preference', 'any').lower()

    for ans in screening_answers or []:
        q = ans.get('question', '').lower()
        a = ans.get('answer', '').lower()

        if ('relocate' in q or 'relocation' in q) and 'remote' not in job_location:
            willing_to_relocate = 'yes' in a or 'willing' in a
            if not willing_to_relocate:
                goal_relocation = goals.get('open_to_relocation', False)
                if not goal_relocation:
                    result['contradictions'].append(
                        f"Answer says not willing to relocate but job is in {job_location}"
                    )

        if ('remote' in q or 'onsite' in q or 'in-office' in q):
            prefers_remote = 'remote' in a.lower()
            job_is_remote = 'remote' in job_location
            if prefers_remote and not job_is_remote and remote_pref == 'remote':
                result['contradictions'].append(
                    "Answer prefers remote but job requires onsite/hybrid and profile prefers remote"
                )

    return result


def _check_education_consistency(resume_data: dict, screening_answers: list, job_data: dict) -> dict:
    result = {'consistent': True, 'contradictions': []}
    education = resume_data.get('education', [])
    job_requirements = job_data.get('requirements', []) if job_data else []

    if not education or not screening_answers:
        return result

    resume_degrees = [str(e.get('degree', '')).lower() for e in education if e.get('degree')]
    resume_fields = [str(e.get('field', '')).lower() for e in education if e.get('field')]

    degree_levels = {
        'bachelor': 1, 'b.s.': 1, 'ba': 1, 'b.a.': 1, 'bs': 1,
        'master': 2, 'm.s.': 2, 'ma': 2, 'm.a.': 2, 'ms': 2, 'mba': 2,
        'phd': 3, 'ph.d': 3, 'doctorate': 3, 'doctor': 3,
    }
    max_resume_level = 0
    for deg in resume_degrees:
        for key, level in degree_levels.items():
            if key in deg:
                max_resume_level = max(max_resume_level, level)

    for req in job_requirements:
        req_lower = req.lower()
        req_level = 0
        for key, level in degree_levels.items():
            if key in req_lower:
                req_level = max(req_level, level)
        if req_level > max_resume_level and max_resume_level > 0:
            result['contradictions'].append(
                f"Job requires higher degree level ({req}) than candidate has "
                f"({', '.join(d[:30] for d in resume_degrees)})"
            )
        elif req_level > 0 and max_resume_level == 0:
            result['contradictions'].append(
                f"Job requires {req} but candidate has no degree listed in resume"
            )

    for ans in screening_answers:
        q = ans.get('question', '').lower()
        a = ans.get('answer', '').lower()
        if ('degree' in q or 'education' in q or 'qualification' in q):
            if resume_degrees and not any(d in a for d in resume_degrees):
                result['contradictions'].append(
                    f"Education answer doesn't reference resume degrees: {', '.join(d[:20] for d in resume_degrees)}"
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
