import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone

from .models import ApplicationOutcome

logger = logging.getLogger(__name__)

# Competitive decay: older postings get more applicants
APPLICANT_ACCUMULATION_PER_DAY = 3.5
MAX_COMPETITIVE_DAYS = 60


def estimate_applicant_count(posted_at: Optional[datetime], reported_count: Optional[int] = None) -> int:
    if reported_count is not None and reported_count > 0:
        return reported_count
    if not posted_at:
        return 0
    days_live = (timezone.now() - posted_at).days
    if days_live < 0:
        return 0
    return min(int(days_live * APPLICANT_ACCUMULATION_PER_DAY), 500)


def score_competitiveness(
    posted_at: Optional[datetime] = None,
    applicant_count: Optional[int] = None,
    company_size: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    total_applicants_estimate: Optional[int] = None,
) -> dict:
    estimated = total_applicants_estimate or estimate_applicant_count(posted_at, applicant_count)

    # Base competitiveness score (higher = more competitive)
    score = 30

    reasons = []

    # Applicant count component
    if estimated > 0:
        app_penalty = min(35, int(estimated / 5))
        score += app_penalty
        reasons.append(f"~{estimated} estimated applicants (+{app_penalty})")

    # Age component
    if posted_at:
        days = max(0, (timezone.now() - posted_at).days)
        if days > MAX_COMPETITIVE_DAYS:
            score += 20
            reasons.append(f"Posted {days}d ago — likely saturated (+20)")
        elif days > 30:
            score += 10
            reasons.append(f"Posted {days}d ago (+10)")
        elif days < 1:
            score -= 10
            reasons.append(f"Fresh posting (<1d) (-10)")

    # Remote jobs are more competitive
    if remote:
        score += 10
        reasons.append("Remote position (+10)")

    # Location-based
    if location:
        competitive_hubs = ['san francisco', 'new york', 'seattle', 'london', 'bangalore',
                            'san jose', 'los angeles', 'austin', 'boston', 'chicago',
                            'berlin', 'amsterdam', 'toronto', 'singapore', 'sydney']
        loc_lower = location.lower()
        for hub in competitive_hubs:
            if hub in loc_lower:
                score += 8
                reasons.append(f"Competitive hub: {location} (+8)")
                break

    # Company size
    if company_size:
        size_lower = company_size.lower()
        if size_lower in ('large', 'enterprise', '10000+', '5000-10000'):
            score += 8
            reasons.append(f"Large company ({company_size}) (+8)")
        elif size_lower in ('medium', 'startup', '1-50', '51-200', '201-500'):
            score -= 5
            reasons.append(f"Smaller company ({company_size}) (-5)")

    score = max(0, min(100, score))

    recommendation = 'apply_soon' if score < 40 else 'apply_now' if score < 60 else 'apply_early' if score < 75 else 'consider_skip'
    return {
        'competitiveness_score': score,
        'estimated_applicants': estimated,
        'recommendation': recommendation,
        'reasons': '; '.join(reasons) if reasons else 'Low competition signals',
    }


def adjust_threshold_for_competition(base_threshold: int, competitiveness_score: int) -> int:
    if competitiveness_score >= 80:
        return min(95, base_threshold + 15)
    elif competitiveness_score >= 60:
        return min(90, base_threshold + 10)
    elif competitiveness_score >= 40:
        return min(85, base_threshold + 5)
    elif competitiveness_score <= 20:
        return max(50, base_threshold - 10)
    return base_threshold


def get_user_competition_insights(user, organization) -> dict:
    recent_outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
    ).select_related('application__job').order_by('-created_at')[:50]

    if not recent_outcomes:
        return {'message': 'No application history for competitive insights'}

    total = len(recent_outcomes)
    interviews = sum(1 for o in recent_outcomes if o.outcome in ('interview', 'offer', 'accepted'))
    success_rate = interviews / total if total else 0

    # Check if success rate correlates with estimated competitiveness
    low_comp_apps = 0
    low_comp_successes = 0
    high_comp_apps = 0
    high_comp_successes = 0

    for ao in recent_outcomes:
        job = ao.application.job
        if not job:
            continue
        comp = score_competitiveness(
            posted_at=job.posted_at,
            applicant_count=job.application_count,
            company_size=job.company.size if job.company else None,
            remote=job.remote,
        )
        cs = comp['competitiveness_score']
        if cs < 50:
            low_comp_apps += 1
            if ao.outcome in ('interview', 'offer', 'accepted'):
                low_comp_successes += 1
        else:
            high_comp_apps += 1
            if ao.outcome in ('interview', 'offer', 'accepted'):
                high_comp_successes += 1

    return {
        'total_applications_analyzed': total,
        'overall_success_rate': round(success_rate, 3),
        'low_competition': {
            'count': low_comp_apps,
            'successes': low_comp_successes,
            'success_rate': round(low_comp_successes / low_comp_apps, 3) if low_comp_apps else 0,
        },
        'high_competition': {
            'count': high_comp_apps,
            'successes': high_comp_successes,
            'success_rate': round(high_comp_successes / high_comp_apps, 3) if high_comp_apps else 0,
        },
    }
