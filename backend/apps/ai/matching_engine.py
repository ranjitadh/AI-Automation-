import json
import logging
from typing import Optional

from django.conf import settings

from .gateway import generate
from .schemas import APPLICATION_DECISION_SCHEMA, EXPERIENCE_CALIBRATION_SCHEMA
from .models import CareerGoal, CareerMemory, ApplicationDecision

logger = logging.getLogger(__name__)


def analyze_job_match(job_data: dict, candidate_data: dict,
                      organization_id: str = None, user_id: str = None) -> dict:
    learned_patterns = candidate_data.get('learned_patterns', [])
    score_adjustments = _compute_learned_adjustments(learned_patterns, job_data)

    system_prompt = (
        "You are a senior recruiting expert and career intelligence analyst. "
        "Analyze this job posting against the candidate's profile with extreme rigor. "
        "Assess skill match, experience match, seniority alignment, industry fit, "
        "salary compatibility, and location feasibility. "
        "Be brutally honest about gaps and overqualification risks. "
        "Return a structured JSON decision. "
        "Never inflate scores. This is for real hiring decisions."
    )
    user_prompt = json.dumps({
        "job": job_data,
        "candidate": candidate_data,
        "instructions": (
            "Extract and calculate each dimension independently: "
            "1. Skill Match: what % of required technologies/skills does candidate possess? "
            "2. Experience Match: does candidate's years/domain experience align? "
            "3. Seniority Match: is candidate's seniority level appropriate for this role? "
            "4. Industry Match: has candidate worked in similar industries? "
            "5. Salary Match: is salary range within candidate's expectations? "
            "6. Location Match: is the location feasible? "
            "Then compute a weighted overall fit_score. "
            "Label overqualification_risk and underqualification_risk honestly. "
            "If candidate is obviously overqualified (e.g., 15yr senior dev applying to internship), "
            "set overqualification_risk to high and recommend reject. "
            "If candidate is obviously underqualified (e.g., missing 5+ required skills), "
            "set underqualification_risk to high and recommend reject. "
            "Only recommend 'apply' if total fit_score >= 70 AND no high risks."
        ),
    })

    result = generate(
        task_type='application_decision',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=APPLICATION_DECISION_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    raw = result.get('parsed', result)

    if score_adjustments and isinstance(raw, dict):
        adjustment = score_adjustments.get('total_adjustment', 0)
        if adjustment != 0:
            old_score = raw.get('fit_score', 50)
            new_score = max(0, min(100, old_score + adjustment))
            raw['fit_score'] = new_score
            raw['fit_score_adjusted'] = True
            raw['fit_score_original'] = old_score
            raw['learning_adjustment'] = adjustment
            raw['learning_reason'] = score_adjustments.get('reason', '')
            logger.info(
                f"Learning adjustment applied: {old_score} -> {new_score} "
                f"({adjustment:+d}) — {score_adjustments.get('reason', '')}"
            )

    return raw


def _compute_learned_adjustments(learned_patterns: list, job_data: dict) -> dict:
    if not learned_patterns:
        return {'total_adjustment': 0, 'reason': 'no patterns'}

    total_adjustment = 0
    reasons = []
    job_title = (job_data.get('title') or '').lower()
    job_industry = (job_data.get('company_industry') or '').lower()
    job_seniority = (job_data.get('seniority') or '').lower()

    for pattern in learned_patterns:
        ptype = pattern.get('type', '')
        pkey = pattern.get('key', '')
        pvalue = pattern.get('value', {})
        confidence = pattern.get('confidence', 0.5)

        if confidence < 0.3:
            continue

        if ptype == 'failure_pattern':
            if pkey == 'missing_skills_rejection':
                total_adjustment -= int(10 * confidence)
                reasons.append(f"pattern: missing skills (confidence {confidence:.1f})")
            elif pkey == 'experience_gap_rejection':
                total_adjustment -= int(10 * confidence)
                reasons.append(f"pattern: experience gap (confidence {confidence:.1f})")
            elif pkey == 'overqualified_rejection':
                total_adjustment -= int(5 * confidence)
                reasons.append(f"pattern: overqualified rejections (confidence {confidence:.1f})")
            elif pkey == 'salary_mismatch_rejection':
                total_adjustment -= int(5 * confidence)
                reasons.append(f"pattern: salary mismatch (confidence {confidence:.1f})")

        elif ptype == 'success_pattern':
            industry = (pvalue.get('industry') or '').lower()
            if industry and industry == job_industry:
                total_adjustment += int(10 * confidence)
                reasons.append(f"pattern: success in {industry} (confidence {confidence:.1f})")
            else:
                total_adjustment += int(3 * confidence)
                reasons.append(f"pattern: general success (confidence {confidence:.1f})")

        elif ptype == 'preference':
            if pkey.startswith('industry_'):
                pref_industry = pkey.replace('industry_', '').lower()
                success_count = int(pvalue.get('success_count', 0) or 0)
                if pref_industry == job_industry and success_count > 0:
                    bonus = min(15, success_count * 3)
                    total_adjustment += bonus
                    reasons.append(f"preferred industry {pref_industry} ({success_count} successes)")

    total_adjustment = max(-30, min(30, total_adjustment))
    reason = '; '.join(reasons) if reasons else 'no relevant patterns'

    return {'total_adjustment': total_adjustment, 'reason': reason}


def calibrate_experience(job_seniority: str, candidate_seniority: str,
                         candidate_years: float, job_years_required: Optional[float],
                         job_data: dict = None, resume_data: dict = None,
                         organization_id: str = None, user_id: str = None) -> dict:
    system_prompt = (
        "You are an experience calibration expert. Your task is to determine how "
        "a candidate's resume should be presented to match a job's seniority level "
        "without fabricating or misrepresenting any information. "
        "If the candidate is overqualified, determine which aspects to de-emphasize "
        "(leadership titles, executive responsibilities) and which to emphasize "
        "(hands-on technical work, relevant projects). "
        "If the candidate is underqualified, identify transferable skills and "
        "adjacent technologies that are relevant. "
        "Never suggest fabricating experience, degrees, certifications, companies, or dates."
    )
    user_prompt = json.dumps({
        "job_seniority": job_seniority,
        "candidate_seniority": candidate_seniority,
        "candidate_years_of_experience": candidate_years,
        "job_years_required": job_years_required,
        "job": job_data or {},
        "resume": resume_data or {},
    })

    result = generate(
        task_type='experience_calibration',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=EXPERIENCE_CALIBRATION_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def decide_application(job_match: dict, calibration: dict,
                       threshold: int = 70, auto_apply: bool = False,
                       user=None, organization=None, job=None) -> ApplicationDecision:
    fit_score = job_match.get('fit_score', 0)
    overqual_risk = job_match.get('overqualification_risk', 'none')
    underqual_risk = job_match.get('underqualification_risk', 'none')
    decision_str = job_match.get('decision', 'reject')

    adjusted_threshold = threshold
    throttle_info = {}
    comp_info = {}
    if user and organization and job:
        try:
            from .salary_throttle_engine import compute_throttle, compute_bid_score
            from .competitive_analysis_engine import score_competitiveness, adjust_threshold_for_competition
            goals = CareerGoal.objects.filter(
                user=user, organization=organization, is_active=True
            ).first()
            if goals:
                t_min = goals.target_salary_min
                t_max = goals.target_salary_max
                throttle_info = compute_throttle(
                    target_salary_min=t_min,
                    target_salary_max=t_max,
                    job_salary_min=job.salary_min,
                    job_salary_max=job.salary_max,
                    job_salary_period=job.salary_period,
                )
                tf = throttle_info.get('throttle_factor', 1.0)
                if tf < 0.3:
                    adjusted_threshold = 95
                elif tf < 0.6:
                    adjusted_threshold = 85
                elif tf < 0.8:
                    adjusted_threshold = 75
                bid = compute_bid_score(
                    fit_score=fit_score,
                    throttle_factor=tf,
                    skill_match_score=job_match.get('skill_match_score', 50),
                    industry_match_score=job_match.get('industry_match_score', 50),
                )
                throttle_info['bid_score'] = bid
                throttle_info['adjusted_threshold'] = adjusted_threshold
        except Exception as e:
            logger.warning(f"Salary throttle failed: {e}")

        try:
            comp_info = score_competitiveness(
                posted_at=job.posted_at,
                applicant_count=job.application_count,
                company_size=job.company.size if job.company else None,
                location=job.location,
                remote=job.remote,
            )
            adjusted_threshold = adjust_threshold_for_competition(
                adjusted_threshold, comp_info['competitiveness_score']
            )
            throttle_info['competitiveness'] = comp_info
        except Exception as e:
            logger.warning(f"Competitive analysis failed: {e}")

    if fit_score < adjusted_threshold:
        decision_str = 'reject'
    elif overqual_risk in ('high', 'medium') or underqual_risk in ('high', 'medium'):
        if decision_str != 'reject':
            decision_str = 'review'

    if user and organization and job:
        reasoning = job_match.get('reasoning', '')
        if throttle_info.get('reason'):
            reasoning += f" | Salary: {throttle_info['reason']} (bid={throttle_info.get('bid_score', '?')})"
        if comp_info.get('reasons'):
            reasoning += f" | Competition: {comp_info.get('reasons', '')}"

        decision = ApplicationDecision.objects.update_or_create(
            user=user,
            organization=organization,
            job=job,
            defaults={
                'decision': decision_str,
                'fit_score': fit_score,
                'skill_match_score': job_match.get('skill_match_score', 0),
                'experience_match_score': job_match.get('experience_match_score', 0),
                'seniority_match_score': job_match.get('seniority_match_score', 0),
                'industry_match_score': job_match.get('industry_match_score', 0),
                'salary_match_score': job_match.get('salary_match_score', 0),
                'location_match_score': job_match.get('location_match_score', 0),
                'overqualification_risk': overqual_risk,
                'underqualification_risk': underqual_risk,
                'auto_reject_reason': job_match.get('auto_reject_reason', ''),
                'reasoning': reasoning,
                'confidence': job_match.get('confidence', 0.5),
                'threshold_used': adjusted_threshold,
                'auto_apply': auto_apply and decision_str == 'apply',
            },
        )[0]
        return decision

    return None


def load_candidate_profile(user, organization) -> dict:
    goals = CareerGoal.objects.filter(
        user=user, organization=organization, is_active=True
    ).first()

    memories = CareerMemory.objects.filter(
        user=user, organization=organization, is_active=True
    ).order_by('-confidence')[:50]

    from apps.resumes.models import Resume
    resume = Resume.objects.filter(
        user=user, organization=organization, is_active=True
    ).first()

    return {
        "goals": {
            "target_titles": goals.target_titles if goals else [],
            "target_salary_min": goals.target_salary_min if goals else None,
            "target_salary_max": goals.target_salary_max if goals else None,
            "target_companies": goals.target_companies if goals else [],
            "target_industries": goals.target_industries if goals else [],
            "target_locations": goals.target_locations if goals else [],
            "remote_preference": goals.remote_preference if goals else "any",
            "seniority_level": goals.seniority_level if goals else None,
            "work_authorization": goals.work_authorization if goals else None,
            "employment_type": goals.employment_type if goals else "full_time",
        },
        "resume": {
            "summary": resume.summary if resume else "",
            "skills": resume.skills if resume else [],
            "experience": resume.experience if resume else [],
            "education": resume.education if resume else [],
            "certifications": resume.certifications if resume else [],
            "years_of_experience": float(resume.years_of_experience) if resume and resume.years_of_experience else 0,
            "seniority_level": resume.seniority_level if resume else "",
            "work_authorization": resume.work_authorization if resume else "",
        } if resume else {},
        "learned_patterns": [
            {"key": m.key, "value": m.value, "confidence": m.confidence, "type": m.memory_type}
            for m in memories
        ],
    }


def build_job_data_from_model(job) -> dict:
    return {
        "title": job.title,
        "company": job.company.name if job.company else "",
        "company_industry": job.company.industry if job.company else "",
        "location": job.location or "",
        "remote": job.remote,
        "hybrid": job.hybrid,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "salary_period": job.salary_period,
        "seniority": job.seniority or "",
        "employment_type": job.employment_type or "full_time",
        "description": job.description or "",
        "requirements": job.requirements or [],
        "responsibilities": job.responsibilities or [],
        "nice_to_have": job.nice_to_have or [],
        "department": job.department or "",
        "function": job.function or "",
        "platform": job.platform or "",
        "apply_url": job.apply_url or job.direct_apply_url or "",
    }
