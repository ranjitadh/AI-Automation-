import json
import logging
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
                    existing.confidence = min(0.95, existing.confidence + 0.05)
                    existing.value['count'] = count
                    existing.value['last_example'] = pattern_data
                    existing.save(update_fields=['value', 'confidence'])
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
            existing.confidence = min(0.95, existing.confidence + 0.05)
            existing.value['success_count'] = existing.value.get('success_count', 0) + 1
            existing.value['last_success'] = success_data
            existing.save(update_fields=['value', 'confidence'])
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

    system_prompt = (
        "You are a career analytics engine. Analyze the user's application outcomes "
        "to identify patterns, what works, what doesn't, and actionable advice. "
        "Focus on: which resume variants perform best, which skills correlate with "
        "interviews, which industries respond, which salary ranges get offers, "
        "and common rejection patterns. "
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
    }


def get_weekly_report(user, organization) -> dict:
    week_ago = timezone.now() - timedelta(days=7)
    week_apps = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
        created_at__gte=week_ago,
    )

    total = week_apps.count()
    interviews = week_apps.filter(outcome='interview').count()
    rejects = week_apps.filter(outcome='rejected').count()

    recent_decisions = ApplicationDecision.objects.filter(
        user=user, organization=organization,
        created_at__gte=week_ago,
    )

    return {
        "week_applications": total,
        "week_interviews": interviews,
        "week_rejects": rejects,
        "decisions_made": recent_decisions.count(),
        "average_fit_score": recent_decisions.aggregate(avg=Avg('fit_score')).get('avg', 0),
        "apply_count": recent_decisions.filter(decision='apply').count(),
        "reject_count": recent_decisions.filter(decision='reject').count(),
        "auto_applied": recent_decisions.filter(auto_apply=True).count(),
    }
