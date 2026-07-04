import json
import logging
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Optional

from django.utils import timezone
from django.db.models import Count, Avg

from .gateway import generate
from .models import CareerMemory, ApplicationDecision, ApplicationOutcome
from .schemas import LEARNING_OUTCOME_SCHEMA

logger = logging.getLogger(__name__)


def record_outcome(application, outcome: str, rejection_reason: str = None,
                   feedback: str = None, interview_rounds: int = None,
                   offer_amount: int = None, resume_version=None,
                   cover_letter_text: str = None) -> ApplicationOutcome:
    user = application.applicant
    org = application.organization

    response_time = None
    if application.submitted_at:
        response_time = (timezone.now() - application.submitted_at).days

    outcome_obj, _ = ApplicationOutcome.objects.update_or_create(
        application=application,
        defaults={
            'user': user,
            'organization': org,
            'outcome': outcome,
            'response_time_days': response_time,
            'interview_rounds': interview_rounds,
            'offer_amount': offer_amount,
            'rejection_reason': rejection_reason,
            'feedback': feedback,
            'resume_version_used': resume_version,
            'cover_letter_version': cover_letter_text,
        },
    )

    if outcome in ('rejected', 'no_response'):
        learn_from_rejection(application, rejection_reason, feedback, user, org)
    elif outcome in ('interview', 'offer', 'accepted'):
        learn_from_success(application, outcome, user, org)

    return outcome_obj


MAX_CONFIDENCE = 0.85
MIN_SAMPLES_FOR_HIGH_CONFIDENCE = 5
PATTERN_DECAY_DAYS = 90


def _decay_confidence(existing_memory) -> float:
    from django.utils import timezone
    if not existing_memory or not existing_memory.updated_at:
        return 0.5
    days_since = (timezone.now() - existing_memory.updated_at).days
    if days_since >= PATTERN_DECAY_DAYS:
        decay_factor = max(0.5, 1.0 - (days_since - PATTERN_DECAY_DAYS) / 90.0)
        return existing_memory.confidence * decay_factor
    return existing_memory.confidence


def learn_from_rejection(application, rejection_reason: str, feedback: str,
                         user, organization):
    job = application.job

    pattern_data = {
        "job_title": job.title,
        "company": job.company.name if job.company else "",
        "industry": job.company.industry if job.company else "",
        "seniority": job.seniority,
        "rejection_reason": rejection_reason or "",
        "feedback": feedback or "",
        "applied_at": str(application.submitted_at) if application.submitted_at else "",
    }

    CareerMemory.objects.update_or_create(
        user=user,
        organization=organization,
        memory_type='failure_pattern',
        key=f"rejected_{job.id}",
        defaults={
            'value': pattern_data,
            'confidence': 0.6,
            'source': 'learning_engine',
        },
    )

    if rejection_reason:
        key_patterns = {
            'skill': 'missing_skills_rejection',
            'experience': 'experience_gap_rejection',
            'overqualified': 'overqualified_rejection',
            'underqualified': 'underqualified_rejection',
            'visa': 'visa_rejection',
            'salary': 'salary_mismatch_rejection',
            'location': 'location_rejection',
        }
        reason_lower = rejection_reason.lower()
        for keyword, pattern_key in key_patterns.items():
            if keyword in reason_lower:
                existing = CareerMemory.objects.filter(
                    user=user, organization=organization,
                    memory_type='failure_pattern', key=pattern_key,
                ).first()
                count = 1
                if existing:
                    count = existing.value.get('count', 0) + 1
                    # Apply time decay before boosting
                    decayed = _decay_confidence(existing)
                    # Cap confidence growth: require min samples for high confidence
                    if count >= MIN_SAMPLES_FOR_HIGH_CONFIDENCE:
                        boost = 0.03
                    else:
                        boost = 0.02
                    existing.confidence = min(MAX_CONFIDENCE, decayed + boost)
                    existing.value['count'] = count
                    existing.value['last_example'] = pattern_data
                    existing.save(update_fields=['value', 'confidence', 'updated_at'])
                else:
                    CareerMemory.objects.create(
                        user=user, organization=organization,
                        memory_type='failure_pattern', key=pattern_key,
                        value={'count': 1, 'last_example': pattern_data},
                        confidence=0.4,
                        source='learning_engine',
                    )
                break


def learn_from_success(application, outcome: str, user, organization):
    from django.utils import timezone
    job = application.job
    success_data = {
        "job_title": job.title,
        "company": job.company.name if job.company else "",
        "industry": job.company.industry if job.company else "",
        "seniority": job.seniority,
        "outcome": outcome,
        "applied_at": str(application.submitted_at) if application.submitted_at else "",
    }

    CareerMemory.objects.update_or_create(
        user=user,
        organization=organization,
        memory_type='success_pattern',
        key=f"{outcome}_{job.id}",
        defaults={
            'value': success_data,
            'confidence': 0.7 if outcome == 'offer' else 0.5,
            'source': 'learning_engine',
        },
    )

    if job.company and job.company.industry:
        industry_key = f"industry_{job.company.industry}"
        existing = CareerMemory.objects.filter(
            user=user, organization=organization,
            memory_type='preference', key=industry_key,
        ).first()
        if existing:
            decayed = _decay_confidence(existing)
            count = existing.value.get('success_count', 0) + 1
            boost = 0.03 if count >= MIN_SAMPLES_FOR_HIGH_CONFIDENCE else 0.02
            existing.confidence = min(MAX_CONFIDENCE, decayed + boost)
            existing.value['success_count'] = count
            existing.value['last_success'] = success_data
            existing.save(update_fields=['value', 'confidence', 'updated_at'])
        else:
            CareerMemory.objects.create(
                user=user, organization=organization,
                memory_type='preference', key=industry_key,
                value={'industry': job.company.industry, 'success_count': 1, 'last_success': success_data},
                confidence=0.5,
                source='learning_engine',
            )


def _compute_resume_variant_performance(applications_data: list) -> list:
    from apps.resumes.models import ResumeVersion
    version_outcomes = {}
    for ao in applications_data:
        rv = ao.resume_version_used
        if rv:
            vkey = str(rv.id)
            if vkey not in version_outcomes:
                version_outcomes[vkey] = {
                    'variant_key': f"v{rv.version_number}",
                    'sample_size': 0,
                    'interview_count': 0,
                    'total': 0,
                    'version_number': rv.version_number,
                }
            version_outcomes[vkey]['total'] += 1
            version_outcomes[vkey]['sample_size'] += 1
            if ao.outcome in ('interview', 'offer', 'accepted'):
                version_outcomes[vkey]['interview_count'] += 1

    result = []
    for vkey, data in version_outcomes.items():
        data['interview_rate'] = round(data['interview_count'] / data['total'], 2) if data['total'] else 0
        del data['interview_count']
        del data['total']
        del data['version_number']
        result.append(data)
    return result


def analyze_trends(user, organization) -> dict:
    all_outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).order_by('created_at')

    if all_outcomes.count() < 5:
        return {"has_data": False, "message": "Need at least 5 outcomes for trend analysis"}

    trends = {}
    for outcome_type in ['interview', 'offer', 'rejected', 'no_response']:
        type_outcomes = all_outcomes.filter(outcome=outcome_type)
        if type_outcomes.count() >= 3:
            recent = type_outcomes.order_by('-created_at')[:3]
            older = type_outcomes.order_by('-created_at')[3:6]
            recent_rate = len(recent) / max(all_outcomes.count(), 1)
            older_rate = len(older) / max(all_outcomes.count(), 1)
            trends[outcome_type] = {
                "recent_count": len(recent),
                "older_count": len(older),
                "trend": "improving" if recent_rate > older_rate else "declining" if recent_rate < older_rate else "stable",
            }

    return {
        "has_data": True,
        "trends": trends,
        "total_outcomes": all_outcomes.count(),
    }


def analyze_patterns(user, organization) -> dict:
    applications_data = list(ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job__company').order_by('-created_at')[:50])

    if not applications_data:
        return {"patterns": [], "message": "Not enough data for analysis"}

    outcomes_by_type = {}
    for ao in applications_data:
        outcomes_by_type.setdefault(ao.outcome, []).append(ao)

    total = len(applications_data)
    interview_count = len(outcomes_by_type.get('interview', []))
    offer_count = len(outcomes_by_type.get('offer', []))
    reject_count = len(outcomes_by_type.get('rejected', []))
    no_response_count = len(outcomes_by_type.get('no_response', []))

    variant_performance = _compute_resume_variant_performance(applications_data)
    trends = analyze_trends(user, organization)

    avg_response_time = None
    responded = [ao for ao in applications_data if ao.response_time_days is not None]
    if responded:
        avg_response_time = sum(ao.response_time_days for ao in responded) / len(responded)

    outcome_breakdown = {}
    for otype, items in outcomes_by_type.items():
        outcome_breakdown[otype] = {
            "count": len(items),
            "percentage": round(len(items) / total * 100, 1),
        }

    system_prompt = (
        "You are a V2 career analytics engine. Analyze the user's application outcomes "
        "to identify patterns, what works, what doesn't, and actionable advice. "
        "Focus on: which resume variants perform best, which skills correlate with "
        "interviews, which industries respond, which salary ranges get offers, "
        "and common rejection patterns. "
        "Also analyze trends — are things improving or declining over time? "
        "Return structured JSON with patterns, best_performing_skills, "
        "best_industries, and optimal_salary_range."
    )

    user_prompt = json.dumps({
        "total_applications": total,
        "interviews": interview_count,
        "offers": offer_count,
        "rejections": reject_count,
        "no_responses": no_response_count,
        "interview_rate": round(interview_count / total, 2) if total else 0,
        "offer_rate": round(offer_count / total, 2) if total else 0,
        "average_response_time_days": avg_response_time,
        "outcome_breakdown": outcome_breakdown,
        "trends": trends,
        "resume_variant_performance": variant_performance,
        "outcomes": [
            {
                "title": ao.application.job.title,
                "company": ao.application.job.company.name if ao.application.job.company else "",
                "industry": ao.application.job.company.industry if ao.application.job.company else "",
                "outcome": ao.outcome,
                "rejection_reason": ao.rejection_reason,
                "response_time_days": ao.response_time_days,
            }
            for ao in applications_data[:30]
        ],
    })

    result = generate(
        task_type='learning_outcome',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=LEARNING_OUTCOME_SCHEMA,
        organization_id=str(organization.id),
        user_id=str(user.id),
    )
    parsed = result.get('parsed', result)

    if parsed and parsed.get('patterns'):
        for p in parsed['patterns']:
            CareerMemory.objects.update_or_create(
                user=user,
                organization=organization,
                memory_type='insight',
                key=p.get('pattern', 'unknown_pattern'),
                defaults={
                    'value': p,
                    'confidence': p.get('confidence', 0.5),
                    'source': 'learning_engine',
                },
            )

    if variant_performance:
        CareerMemory.objects.update_or_create(
            user=user,
            organization=organization,
            memory_type='insight',
            key='resume_variant_performance',
            defaults={
                'value': {'variants': variant_performance},
                'confidence': 0.7,
                'source': 'learning_engine',
            },
        )

    return {
        "patterns": parsed.get('patterns', []) if parsed else [],
        "resume_variant_performance": variant_performance,
        "best_performing_skills": parsed.get('best_performing_skills', []) if parsed else [],
        "best_industries": parsed.get('best_industries', []) if parsed else [],
        "optimal_salary_range": parsed.get('optimal_salary_range', {}) if parsed else {},
        "trends": trends,
        "outcome_breakdown": outcome_breakdown,
        "average_response_time_days": avg_response_time,
    }


def get_skill_weights(user, organization) -> dict:
    weights = {}
    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job').order_by('-created_at')[:100]

    skill_outcomes = defaultdict(list)
    for ao in outcomes:
        job = ao.application.job
        if not job:
            continue
        required_skills = set(s.lower() for s in (job.required_skills or []))
        for skill in required_skills:
            skill_outcomes[skill].append(ao.outcome)

    for skill, outcomes_list in skill_outcomes.items():
        total = len(outcomes_list)
        if total < 2:
            weights[skill] = 1.0
            continue
        interview_count = sum(1 for o in outcomes_list if o in ('interview', 'offer', 'accepted'))
        rate = interview_count / total
        weights[skill] = round(0.5 + rate * 0.5, 2)

    return weights


def get_industry_weights(user, organization) -> dict:
    weights = {}
    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job__company').order_by('-created_at')[:100]

    industry_outcomes = defaultdict(list)
    for ao in outcomes:
        company = ao.application.job.company if ao.application.job else None
        if not company or not company.industry:
            continue
        industry_outcomes[company.industry].append(ao.outcome)

    for industry, outcomes_list in industry_outcomes.items():
        total = len(outcomes_list)
        if total < 2:
            weights[industry] = 1.0
            continue
        interview_count = sum(1 for o in outcomes_list if o in ('interview', 'offer', 'accepted'))
        rate = interview_count / total
        weights[industry] = round(0.5 + rate * 0.5, 2)

    return weights


def get_seeded_skill_weights() -> dict:
    """Cold-start seeding: industry baseline weights for common skills."""
    return {
        "python": 1.15, "javascript": 1.12, "typescript": 1.15,
        "react": 1.10, "node.js": 1.10, "aws": 1.12,
        "docker": 1.08, "kubernetes": 1.10, "sql": 1.05,
        "git": 1.03, "ci/cd": 1.08, "rest api": 1.05,
        "graphql": 1.08, "django": 1.08, "fastapi": 1.10,
        "postgresql": 1.05, "redis": 1.05, "terraform": 1.10,
        "machine learning": 1.12, "data science": 1.10,
    }


def get_skill_weights(user, organization) -> dict:
    weights = {}
    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job').order_by('-created_at')[:100]

    skill_outcomes = defaultdict(list)
    for ao in outcomes:
        job = ao.application.job
        if not job:
            continue
        required_skills = set(s.lower() for s in (job.required_skills or []))
        for skill in required_skills:
            skill_outcomes[skill].append(ao.outcome)

    # Use seeded weights as baseline
    seeded = get_seeded_skill_weights()

    for skill, outcomes_list in skill_outcomes.items():
        total = len(outcomes_list)
        if total < 2:
            weights[skill] = seeded.get(skill, 1.0)
            continue
        interview_count = sum(1 for o in outcomes_list if o in ('interview', 'offer', 'accepted'))
        rate = interview_count / total
        computed = round(0.5 + rate * 0.5, 2)
        # Blend with seed: more weight on seed when sample small
        blend = min(total / 10.0, 0.5)
        weights[skill] = round(computed * (1 - blend) + seeded.get(skill, 1.0) * blend, 2)

    # Fill in any missing skills from seeds
    for skill, w in seeded.items():
        if skill not in weights:
            weights[skill] = w

    return weights


def get_industry_weights(user, organization) -> dict:
    weights = {}
    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job__company').order_by('-created_at')[:100]

    industry_outcomes = defaultdict(list)
    for ao in outcomes:
        company = ao.application.job.company if ao.application.job else None
        if not company or not company.industry:
            continue
        industry_outcomes[company.industry].append(ao.outcome)

    for industry, outcomes_list in industry_outcomes.items():
        total = len(outcomes_list)
        if total < 2:
            weights[industry] = 1.0
            continue
        interview_count = sum(1 for o in outcomes_list if o in ('interview', 'offer', 'accepted'))
        rate = interview_count / total
        weights[industry] = round(0.5 + rate * 0.5, 2)

    return weights


def get_boosted_fit_score(base_fit_score: float, profile_data: dict, job_data: dict,
                          user, organization) -> float:
    skill_weights = get_skill_weights(user, organization)
    industry_weights = get_industry_weights(user, organization)

    boost = 0.0
    job_skills = [s.lower() for s in job_data.get('required_skills', [])] if job_data else []
    for skill in job_skills:
        weight = skill_weights.get(skill, 1.0)
        if weight > 1.0:
            boost += (weight - 1.0) * 3

    company = job_data.get('company') if job_data else None
    if company and hasattr(company, 'industry') and company.industry:
        ind_weight = industry_weights.get(company.industry, 1.0)
        if ind_weight > 1.0:
            boost += (ind_weight - 1.0) * 5

    boosted = base_fit_score + boost
    return round(min(100, max(0, boosted)), 1)


def record_boost_feedback(base_fit_score: float, boosted_score: float, outcome: str,
                           job_data: dict, user, organization) -> None:
    """Close the feedback loop: if boosted score led to failure, decrement weights."""
    if outcome in ('rejected', 'no_response') and boosted_score > base_fit_score:
        boost_amount = boosted_score - base_fit_score
        # Find inflated skills and decrement
        skill_weights = get_skill_weights(user, organization)
        job_skills = [s.lower() for s in job_data.get('required_skills', [])] if job_data else []
        penalty = boost_amount / max(len(job_skills), 1) * 0.1
        for skill in job_skills:
            current = skill_weights.get(skill, 1.0)
            if current > 1.0:
                new_weight = max(0.5, current - penalty)
                CareerMemory.objects.update_or_create(
                    user=user, organization=organization,
                    memory_type='feedback',
                    key=f"skill_weight_{skill}",
                    defaults={
                        'value': {
                            'skill': skill,
                            'previous_weight': current,
                            'new_weight': new_weight,
                            'outcome': outcome,
                            'boost_that_failed': boost_amount,
                        },
                        'confidence': 0.6,
                        'source': 'learning_engine',
                    },
                )


def get_weekly_report(user, organization) -> dict:
    week_ago = timezone.now() - timedelta(days=7)
    week_apps = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
        created_at__gte=week_ago,
    )

    total = week_apps.count()
    interviews = week_apps.filter(outcome='interview').count()
    rejects = week_apps.filter(outcome='rejected').count()
    screens = week_apps.filter(outcome='screen').count()
    offers = week_apps.filter(outcome='offer').count()

    recent_decisions = ApplicationDecision.objects.filter(
        user=user, organization=organization,
        created_at__gte=week_ago,
    )

    return {
        "week_applications": total,
        "week_interviews": interviews,
        "week_screens": screens,
        "week_offers": offers,
        "week_rejects": rejects,
        "decisions_made": recent_decisions.count(),
        "average_fit_score": recent_decisions.aggregate(avg=Avg('fit_score')).get('avg', 0),
        "apply_count": recent_decisions.filter(decision='apply').count(),
        "reject_count": recent_decisions.filter(decision='reject').count(),
        "review_count": recent_decisions.filter(decision='review').count(),
        "queue_count": recent_decisions.filter(decision='queue').count(),
        "auto_applied": recent_decisions.filter(auto_apply=True).count(),
        "outcome_breakdown": {
            "total": total,
            "interviews": interviews,
            "screens": screens,
            "offers": offers,
            "rejects": rejects,
        },
    }
