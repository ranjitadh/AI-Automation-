import logging
from typing import Optional

logger = logging.getLogger(__name__)

SALARY_PERIOD_MULTIPLIERS = {
    'yearly': 1.0,
    'annual': 1.0,
    'monthly': 12.0,
    'weekly': 52.0,
    'daily': 260.0,
    'hourly': 2080.0,
}


def _normalize_to_yearly(amount: Optional[int], period: str = 'yearly') -> Optional[float]:
    if amount is None:
        return None
    multiplier = SALARY_PERIOD_MULTIPLIERS.get(period.lower(), 1.0)
    return float(amount) * multiplier


def compute_throttle(
    target_salary_min: Optional[float],
    target_salary_max: Optional[float],
    job_salary_min: Optional[float],
    job_salary_max: Optional[float],
    job_salary_period: str = 'yearly',
    target_salary_period: str = 'yearly',
) -> dict:
    if target_salary_min is None and target_salary_max is None:
        return {'throttle_factor': 1.0, 'bid_score': 75, 'reason': 'No salary targets set'}

    job_min = _normalize_to_yearly(job_salary_min, job_salary_period)
    job_max = _normalize_to_yearly(job_salary_max, job_salary_period)
    tgt_min = _normalize_to_yearly(target_salary_min, target_salary_period)
    tgt_max = _normalize_to_yearly(target_salary_max, target_salary_period)

    if job_min is None and job_max is None:
        return {'throttle_factor': 0.7, 'bid_score': 50, 'reason': 'Job salary not disclosed'}

    job_mid = ((job_min or 0) + (job_max or 200000)) / 2.0
    candidate_mid = ((tgt_min or 0) + (tgt_max or 200000)) / 2.0

    if job_max is not None and tgt_min is not None and job_max < tgt_min * 0.85:
        ratio = job_max / max(tgt_min, 1)
        # Scale: ratio=0.85 (threshold) → 0.5, ratio=0.0 → 0.0
        throttle = max(0.0, ratio / 0.85 * 0.5)
        bid = max(0, int(ratio * 40))
        return {
            'throttle_factor': round(throttle, 2),
            'bid_score': bid,
            'reason': f'Job max (${job_max:,.0f}) is below 85% of target min (${tgt_min:,.0f})',
        }

    if job_min is not None and tgt_max is not None and job_min > tgt_max * 1.5:
        throttle = 0.5
        bid = 60
        return {
            'throttle_factor': throttle,
            'bid_score': bid,
            'reason': f'Job min (${job_min:,.0f}) exceeds 150% of target max (${tgt_max:,.0f}) — may be overqualified',
        }

    if tgt_min is not None and tgt_max is not None:
        overlap_min = max(job_min or 0, tgt_min)
        overlap_max = min(job_max or 999999, tgt_max)
        if overlap_max > overlap_min:
            overlap = (overlap_max - overlap_min) / ((job_max or overlap_max) - (job_min or overlap_min))
            throttle = min(1.0, 0.7 + overlap * 0.3)
            bid = int(60 + overlap * 35)
            return {
                'throttle_factor': round(throttle, 2),
                'bid_score': min(95, bid),
                'reason': f'Salary overlap: ${overlap_min:,.0f}–${overlap_max:,.0f}',
            }

    # Partial overlap or one-sided
    if tgt_min is not None and job_max is not None and job_max >= tgt_min:
        gap = max(0, tgt_min - (job_min or 0))
        if gap == 0:
            throttle = 1.0
            bid = 85
        else:
            gap_ratio = gap / max(tgt_min, 1)
            throttle = max(0.5, 1.0 - gap_ratio)
            bid = max(40, int(80 - gap_ratio * 40))
        return {
            'throttle_factor': round(throttle, 2),
            'bid_score': bid,
            'reason': f'Job range ${job_min or 0:,.0f}–${job_max or 0:,.0f} vs target ${tgt_min:,.0f}–${tgt_max or 0:,.0f}',
        }

    return {'throttle_factor': 0.5, 'bid_score': 40, 'reason': 'Salary range unclear'}


def compute_bid_score(
    fit_score: int,
    throttle_factor: float,
    skill_match_score: int = 50,
    industry_match_score: int = 50,
) -> int:
    # When throttle is low, heavily discount fit_score contribution
    effective_fit = fit_score * throttle_factor
    raw = (
        effective_fit * 0.40 +
        throttle_factor * 100 * 0.30 +
        skill_match_score * 0.20 +
        industry_match_score * 0.10
    )
    return max(0, min(100, int(raw)))
