import json
import logging
from typing import Optional

from .gateway import generate
from .schemas import APPLICATION_VALIDATION_SCHEMA
from .consistency_engine import verify_application_consistency

logger = logging.getLogger(__name__)


def validate_application(resume_exists: bool, cover_letter_exists: bool,
                         fit_score: int, fit_threshold: int,
                         answers_generated: bool, candidate_data: dict = None,
                         application_data: dict = None,
                         organization_id: str = None,
                         user_id: str = None) -> dict:
    system_prompt = (
        "You are a senior application quality assurance validator. "
        "Your job is to verify that an application is ready to submit. "
        "Check for consistency, completeness, and red flags. "
        "If ANY validation check fails, do NOT approve submission. "
        "Queue for review instead. "
        "Checks performed: "
        "1. Resume exists and is populated "
        "2. Cover letter exists and is substantive (not placeholder text) "
        "3. Fit score meets minimum threshold "
        "4. Screening questions have been answered "
        "5. Answers are consistent with resume/profile (no contradictions) "
        "6. Application data is internally consistent "
        "Return structured validation result with pass/fail per check, "
        "warnings, blockers, and final decision (submit/queue_for_review/block)."
    )

    checks_passed = {
        "resume_exists": bool(resume_exists),
        "cover_letter_exists": bool(cover_letter_exists),
        "fit_score_acceptable": fit_score >= fit_threshold,
        "answers_generated": bool(answers_generated),
    }

    user_prompt = json.dumps({
        "checks": checks_passed,
        "fit_score": fit_score,
        "fit_threshold": fit_threshold,
        "candidate": candidate_data or {},
        "application": application_data or {},
        "instructions": (
            "Evaluate each check. If resume_exists is false: blocker. "
            "If cover_letter_exists is false: queue for review. "
            "If fit_score_acceptable is false: queue for review (maybe override). "
            "If answers_generated is false: queue for review. "
            "Check for profile_consistent: verify the answers don't contradict "
            "the resume (e.g., claiming 10 years experience when resume shows 3). "
            "Check for no_contradictions: verify the application data is "
            "internally consistent. "
            "Final decision logic: "
            "- All checks pass AND no blockers -> submit "
            "- Any non-critical check fails -> queue_for_review "
            "- Any critical check fails (resume_exists=false) -> block"
        ),
    })

    result = generate(
        task_type='application_validation',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=APPLICATION_VALIDATION_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def validate_before_submission(application_data: dict) -> dict:
    checks = {}
    blockers = []
    warnings = []

    resume_data = application_data.get('resume', {})
    cover_letter = application_data.get('cover_letter', '')
    answers = application_data.get('answers', [])
    fit_score = application_data.get('fit_score', 0)
    threshold = application_data.get('threshold', 70)
    profile_data = application_data.get('profile', {})
    job_data = application_data.get('job', {})
    candidate_data = application_data.get('candidate_data', profile_data.get('resume', {}))

    checks['resume_exists'] = bool(resume_data) and bool(resume_data.get('adapted_text'))
    if not checks['resume_exists']:
        blockers.append("No adapted resume available")

    checks['cover_letter_exists'] = bool(cover_letter) and len(cover_letter) > 50
    if not checks['cover_letter_exists']:
        warnings.append("Cover letter missing or too short")

    checks['fit_score_acceptable'] = fit_score >= threshold
    if not checks['fit_score_acceptable']:
        warnings.append(f"Fit score {fit_score} below threshold {threshold}")

    checks['answers_generated'] = len(answers) > 0
    if not checks['answers_generated']:
        warnings.append("Screening questions not answered")

    salary_min = application_data.get('salary_min')
    salary_max = application_data.get('salary_max')
    if salary_min and salary_max:
        if salary_max < salary_min:
            blockers.append(f"Salary range inverted: min ${salary_min} > max ${salary_max}")

    visa_needed = application_data.get('visa_sponsorship_needed', False)
    work_auth = application_data.get('work_authorization', '')
    if visa_needed and not work_auth:
        blockers.append("Visa sponsorship needed but no work authorization configured")

    if candidate_data and job_data:
        consistency = verify_application_consistency(
            resume_data=candidate_data,
            cover_letter_text=cover_letter,
            screening_answers=answers,
            profile_data=profile_data,
            job_data=job_data,
        )
        checks['profile_consistent'] = consistency.get('is_consistent', True)
        checks['no_contradictions'] = consistency.get('can_submit', True)
        if consistency.get('contradictions'):
            warnings.extend(consistency['contradictions'][:5])
        if consistency.get('blockers'):
            blockers.extend(consistency['blockers'])
    else:
        checks['profile_consistent'] = True
        checks['no_contradictions'] = True

    if blockers:
        decision = 'block'
    elif warnings and not all(checks.get(k, True) for k in
                               ['resume_exists', 'cover_letter_exists', 'fit_score_acceptable']):
        decision = 'queue_for_review'
    else:
        decision = 'submit'

    return {
        "is_valid": decision == 'submit',
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
        "decision": decision,
    }


def _compute_skill_overlap(resume_skills: list, job_skills: list) -> float:
    if not job_skills:
        return 1.0
    rset = set(s.lower() for s in resume_skills)
    jset = set(s.lower() for s in job_skills)
    if not jset:
        return 1.0
    return len(rset & jset) / len(jset)


def _compute_experience_ratio(candidate_years: float, job_years: float) -> float:
    if not job_years:
        return 1.0
    return candidate_years / job_years if job_years else 1.0


def check_trust_and_safety(application_data: dict) -> dict:
    checks = []
    reject_reasons = []
    can_auto_submit = True

    resume_data = application_data.get('resume', {})
    cover_letter = application_data.get('cover_letter', '')
    answers = application_data.get('answers', [])
    fit_score = application_data.get('fit_score', 0)
    threshold = application_data.get('threshold', 70)
    profile = application_data.get('profile', {})
    job = application_data.get('job', {})
    validation_score = application_data.get('validation_score', 0)
    quality_score = application_data.get('quality_score', 0)
    consistency_score = application_data.get('consistency_score', 100)

    if not resume_data:
        reject_reasons.append("NO_RESUME")
        checks.append({"check": "resume_exists", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "resume_exists", "pass": True, "blocker": True})

    if not cover_letter or len(cover_letter) < 50:
        reject_reasons.append("NO_COVER_LETTER")
        checks.append({"check": "cover_letter_exists", "pass": False, "blocker": False})
        can_auto_submit = False
    else:
        checks.append({"check": "cover_letter_exists", "pass": True})

    if fit_score < threshold:
        reject_reasons.append("LOW_FIT_SCORE")
        checks.append({"check": "fit_score", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "fit_score", "pass": True})

    if not answers:
        reject_reasons.append("NO_ANSWERS")
        checks.append({"check": "answers_generated", "pass": False, "blocker": False})
        can_auto_submit = False
    else:
        low_conf = sum(1 for a in answers if isinstance(a, dict) and a.get('confidence', 1) < 0.3)
        if low_conf > 0:
            reject_reasons.append(f"LOW_CONFIDENCE_ANSWERS ({low_conf})")
            checks.append({"check": "answer_confidence", "pass": False, "blocker": True})
            can_auto_submit = False
        else:
            checks.append({"check": "answer_confidence", "pass": True})

    profile_skills = profile.get('skills', [])
    if len(profile_skills) < 3:
        reject_reasons.append("INCOMPLETE_PROFILE")
        checks.append({"check": "profile_completeness", "pass": False, "blocker": False})
    else:
        checks.append({"check": "profile_completeness", "pass": True})

    job_title = (job.get('title') or '').lower()
    excluded = profile.get('excluded_titles', [])
    if excluded and any(e.lower() in job_title for e in excluded):
        reject_reasons.append("EXCLUDED_TITLE")
        checks.append({"check": "title_excluded", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "title_excluded", "pass": True})

    excluded_companies = profile.get('excluded_companies', [])
    company = (job.get('company_name') or job.get('company') or '').lower()
    if excluded_companies and any(ec.lower() in company for ec in excluded_companies):
        reject_reasons.append("EXCLUDED_COMPANY")
        checks.append({"check": "company_excluded", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "company_excluded", "pass": True})

    salary_min = application_data.get('salary_min')
    salary_max = application_data.get('salary_max')
    if salary_min and salary_max and salary_max < salary_min:
        reject_reasons.append("INVERTED_SALARY")
        checks.append({"check": "salary_range", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "salary_range", "pass": True})

    visa_needed = application_data.get('visa_sponsorship_needed', False)
    work_auth = application_data.get('work_authorization', '')
    if visa_needed and not work_auth:
        reject_reasons.append("VISA_NO_AUTH")
        checks.append({"check": "visa_authorization", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "visa_authorization", "pass": True})

    # ── FIX #1: APPLICATION GATING ────────────────────────────
    resume_skills = resume_data.get('skills', [])
    job_skills = job.get('required_skills', [])
    skill_overlap = _compute_skill_overlap(resume_skills, job_skills)
    if skill_overlap < 0.60:
        reject_reasons.append(f"LOW_SKILL_OVERLAP ({skill_overlap:.0%})")
        checks.append({"check": "skill_overlap_60pct", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "skill_overlap_60pct", "pass": True})

    candidate_years = resume_data.get('years_of_experience', 0) or 0
    job_years = job.get('years_experience_required', 0) or job.get('years_required', 0) or 0
    if candidate_years and job_years:
        ratio = _compute_experience_ratio(float(candidate_years), float(job_years))
        if ratio < 0.6:
            reject_reasons.append(f"UNDERQUALIFIED_EXPERIENCE (ratio={ratio:.1f}x)")
            checks.append({"check": "experience_ratio_0.6x", "pass": False, "blocker": True})
            can_auto_submit = False
        elif ratio > 1.5:
            reject_reasons.append(f"OVERQUALIFIED_EXPERIENCE (ratio={ratio:.1f}x)")
            checks.append({"check": "experience_ratio_1.5x", "pass": False, "blocker": True})
            can_auto_submit = False
        else:
            checks.append({"check": "experience_ratio", "pass": True})
    else:
        checks.append({"check": "experience_ratio", "pass": True})

    if fit_score < 75:
        reject_reasons.append(f"FIT_SCORE_BELOW_75 ({fit_score})")
        checks.append({"check": "fit_score_75", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "fit_score_75", "pass": True})

    if validation_score < 80:
        reject_reasons.append(f"VALIDATION_SCORE_BELOW_80 ({validation_score})")
        checks.append({"check": "validation_score_80", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "validation_score_80", "pass": True})

    if consistency_score < 90:
        reject_reasons.append(f"CONSISTENCY_SCORE_BELOW_90 ({consistency_score})")
        checks.append({"check": "consistency_score_90", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "consistency_score_90", "pass": True})

    if quality_score < 85:
        reject_reasons.append(f"QUALITY_SCORE_BELOW_85 ({quality_score})")
        checks.append({"check": "quality_score_85", "pass": False, "blocker": True})
        can_auto_submit = False
    else:
        checks.append({"check": "quality_score_85", "pass": True})
    # ── END APPLICATION GATING ────────────────────────────────

    all_pass = all(c.get('pass', False) for c in checks)
    has_blockers = any(c.get('blocker', False) for c in checks if not c.get('pass', False))

    if has_blockers:
        decision = 'block'
    elif not all_pass:
        decision = 'queue_for_review'
    elif can_auto_submit:
        decision = 'submit'
    else:
        decision = 'queue_for_review'

    return {
        "trust_check_passed": decision == 'submit',
        "can_auto_submit": can_auto_submit,
        "decision": decision,
        "checks": checks,
        "reject_reasons": reject_reasons,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c.get('pass', False)),
        "failed": sum(1 for c in checks if not c.get('pass', False)),
    }
