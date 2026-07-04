import logging
import math
from collections import defaultdict
from typing import Optional

from django.db.models import Count, Q

from .models import ApplicationOutcome

logger = logging.getLogger(__name__)


def _z_score_for_confidence(confidence_pct: float = 95.0) -> float:
    if confidence_pct >= 99:
        return 2.576
    elif confidence_pct >= 95:
        return 1.96
    elif confidence_pct >= 90:
        return 1.645
    elif confidence_pct >= 80:
        return 1.282
    return 1.0


def _wilson_score_interval(positive: int, total: int, z: float = 1.96) -> tuple:
    if total == 0:
        return (0.0, 0.0, 0.0)
    p = positive / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return (centre - margin, centre + margin, p)


def get_version_performance(
    user, organization,
    min_samples: int = 3,
    confidence_level: float = 95.0,
    success_outcomes: tuple = ('interview', 'offer', 'accepted'),
) -> list:
    z = _z_score_for_confidence(confidence_level)

    versions_data = defaultdict(lambda: {
        'total': 0, 'successes': 0, 'rejects': 0, 'no_responses': 0,
    })

    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
        resume_version_used__isnull=False,
    ).select_related('resume_version_used', 'resume_version_used__resume')

    for ao in outcomes:
        rv = ao.resume_version_used
        key = str(rv.id)
        vd = versions_data[key]
        vd['total'] += 1
        if ao.outcome in success_outcomes:
            vd['successes'] += 1
        elif ao.outcome == 'rejected':
            vd['rejects'] += 1
        else:
            vd['no_responses'] += 1

        vd['version_number'] = rv.version_number
        vd['version_id'] = str(rv.id)
        vd['resume_title'] = rv.resume.title if rv.resume else 'Unknown'

    results = []
    for key, data in versions_data.items():
        if data['total'] < min_samples:
            continue
        lo, hi, rate = _wilson_score_interval(data['successes'], data['total'], z)
        data['success_rate'] = round(rate, 3)
        data['ci_lower'] = round(lo, 3)
        data['ci_upper'] = round(hi, 3)
        data['confidence_level'] = confidence_level
        results.append(data)

    results.sort(key=lambda r: r['success_rate'], reverse=True)
    return results


def get_best_version(user, organization, min_samples: int = 3) -> Optional[dict]:
    versions = get_version_performance(user, organization, min_samples=min_samples)
    if not versions:
        return None
    best = versions[0]
    if len(versions) > 1:
        second = versions[1]
        # Check if winner is statistically significant
        if best['ci_lower'] > second['ci_upper']:
            best['statistically_significant'] = True
            best['vs_runner_up'] = {
                'version_id': second['version_id'],
                'success_rate': second['success_rate'],
                'improvement': round(best['success_rate'] - second['success_rate'], 3),
            }
        else:
            best['statistically_significant'] = False
    else:
        best['statistically_significant'] = False
    return best


def get_ab_test_summary(user, organization) -> dict:
    versions = get_version_performance(user, organization, min_samples=1)
    total_apps = sum(v['total'] for v in versions)
    total_successes = sum(v['successes'] for v in versions)

    best = get_best_version(user, organization)
    recommendation = None
    if best and versions:
        worst = versions[-1]
        improvement = best['success_rate'] - worst['success_rate']
        if improvement > 0.05 and best['total'] >= 5:
            recommendation = {
                'best_version_id': best['version_id'],
                'best_version_number': best.get('version_number'),
                'best_success_rate': best['success_rate'],
                'worst_version_id': worst['version_id'],
                'worst_success_rate': worst['success_rate'],
                'improvement': round(improvement, 3),
                'switch_to_best_estimated_gain': int(improvement * total_apps),
            }

    return {
        'total_applications_tracked': total_apps,
        'total_successes': total_successes,
        'overall_success_rate': round(total_successes / total_apps, 3) if total_apps else 0,
        'versions_tested': len(versions),
        'version_performance': versions[:10],
        'best_version': best,
        'recommendation': recommendation,
    }
