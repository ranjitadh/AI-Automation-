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

    location = application_data.get('location', '')
    remote = application_data.get('remote', False)
    if location and 'remote' not in location.lower():
        if not remote:
            pass

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
