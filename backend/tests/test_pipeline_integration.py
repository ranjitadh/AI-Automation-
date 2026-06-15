import pytest
from datetime import datetime, timedelta

from django.utils import timezone

from apps.ai.salary_throttle_engine import (
    compute_throttle,
    compute_bid_score,
    _normalize_to_yearly,
)

from apps.ai.ab_testing_engine import (
    _wilson_score_interval,
    _z_score_for_confidence,
)

from apps.ai.competitive_analysis_engine import (
    score_competitiveness,
    adjust_threshold_for_competition,
    estimate_applicant_count,
)


SAMPLE_JOB_DATA = {
    "title": "Senior Software Engineer",
    "company": "Tech Corp",
    "salary_min": 150000,
    "salary_max": 200000,
    "salary_currency": "USD",
    "salary_period": "yearly",
    "location": "San Francisco, CA",
    "remote": False,
    "posted_at": datetime(2026, 6, 1),
    "company_size": "large",
}

SAMPLE_CANDIDATE_GOALS = {
    "target_salary_min": 140000,
    "target_salary_max": 190000,
}


class TestSalaryThrottleEngine:
    def test_normalize_yearly(self):
        assert _normalize_to_yearly(100, 'yearly') == 100.0
        assert _normalize_to_yearly(100, 'hourly') == 208000.0
        assert _normalize_to_yearly(10000, 'monthly') == 120000.0
        assert _normalize_to_yearly(2000, 'weekly') == 104000.0
        assert _normalize_to_yearly(None, 'yearly') is None

    def test_throttle_no_targets(self):
        result = compute_throttle(None, None, 100000, 150000)
        assert result['throttle_factor'] == 1.0
        assert result['bid_score'] == 75

    def test_throttle_job_below_target(self):
        result = compute_throttle(140000, 190000, 80000, 100000)
        assert result['throttle_factor'] < 0.5
        assert result['bid_score'] < 50
        assert 'below' in result['reason'].lower()

    def test_throttle_job_above_target(self):
        result = compute_throttle(100000, 130000, 200000, 250000)
        assert result['throttle_factor'] <= 0.6
        assert 'overqualified' in result['reason'].lower()

    def test_throttle_good_overlap(self):
        result = compute_throttle(140000, 190000, 150000, 200000)
        assert result['throttle_factor'] >= 0.7
        assert result['bid_score'] >= 60
        assert 'overlap' in result['reason'].lower()

    def test_throttle_no_job_salary(self):
        result = compute_throttle(140000, 190000, None, None)
        assert result['throttle_factor'] == 0.7
        assert result['bid_score'] == 50

    def test_throttle_job_min_only(self):
        result = compute_throttle(140000, 190000, 160000, None)
        assert result['throttle_factor'] >= 0.5

    def test_bid_score_calculation(self):
        score = compute_bid_score(fit_score=80, throttle_factor=0.8, skill_match_score=70, industry_match_score=60)
        assert 0 <= score <= 100
        assert score > 50

    def test_bid_score_low_throttle(self):
        score = compute_bid_score(fit_score=80, throttle_factor=0.1, skill_match_score=70, industry_match_score=60)
        assert score < 50

    def test_bid_score_bounds(self):
        assert compute_bid_score(0, 0.0, 0, 0) == 0
        assert compute_bid_score(100, 1.0, 100, 100) == 100

    def test_throttle_hourly_job(self):
        result = compute_throttle(
            140000, 190000, 70, 90,
            job_salary_period='hourly',
        )
        job_mid_yearly = (70 + 90) / 2 * 2080
        assert result['throttle_factor'] >= 0.7
        assert job_mid_yearly > 140000

    def test_throttle_edge_low(self):
        result = compute_throttle(100000, 150000, 1000, 2000)
        assert result['throttle_factor'] < 0.1
        assert result['bid_score'] < 10

    def test_throttle_partial_overlap_low_end(self):
        result = compute_throttle(120000, 180000, 100000, 130000)
        assert 0.5 <= result['throttle_factor'] <= 1.0


class TestABTestingEngine:
    def test_wilson_interval(self):
        lo, hi, rate = _wilson_score_interval(8, 10, 1.96)
        assert 0 <= lo <= hi <= 1
        assert rate == 0.8

    def test_wilson_interval_zero_total(self):
        lo, hi, rate = _wilson_score_interval(0, 0, 1.96)
        assert lo == 0.0
        assert hi == 0.0

    def test_wilson_interval_all_successes(self):
        lo, hi, rate = _wilson_score_interval(10, 10, 1.96)
        assert rate == 1.0

    def test_wilson_interval_no_successes(self):
        lo, hi, rate = _wilson_score_interval(0, 10, 1.96)
        assert rate == 0.0

    def test_z_score_levels(self):
        assert _z_score_for_confidence(99) == 2.576
        assert _z_score_for_confidence(95) == 1.96
        assert _z_score_for_confidence(90) == 1.645
        assert _z_score_for_confidence(80) == 1.282
        assert _z_score_for_confidence(50) == 1.0

    def test_wilson_small_sample(self):
        lo, hi, rate = _wilson_score_interval(1, 3, 1.96)
        assert 0 <= lo <= hi <= 1
        assert rate == pytest.approx(1 / 3, 0.01)


class TestCompetitiveAnalysisEngine:
    def test_score_competitiveness_fresh_posting(self):
        result = score_competitiveness(
            posted_at=timezone.now(),
            applicant_count=0,
            remote=False,
            location="Rural, USA",
            company_size="startup",
        )
        assert 0 <= result['competitiveness_score'] <= 100
        assert result['estimated_applicants'] == 0

    def test_score_competitiveness_old_posting(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=45),
            applicant_count=None,
            remote=True,
            location="San Francisco, CA",
            company_size="large",
        )
        assert result['competitiveness_score'] >= 50
        assert result['estimated_applicants'] > 100
        assert result['recommendation'] in ('apply_soon', 'apply_now', 'apply_early', 'consider_skip')

    def test_score_competitiveness_high_applicants(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=5),
            applicant_count=200,
            remote=False,
            location="Austin, TX",
            company_size="enterprise",
        )
        assert result['competitiveness_score'] > 40

    def test_estimate_applicant_count(self):
        assert estimate_applicant_count(None) == 0
        assert estimate_applicant_count(timezone.now()) == 0
        old = timezone.now() - timedelta(days=10)
        assert estimate_applicant_count(old) == 35  # 10 * 3.5
        assert estimate_applicant_count(None, reported_count=100) == 100

    def test_adjust_threshold_no_change(self):
        assert adjust_threshold_for_competition(70, 30) == 70

    def test_adjust_threshold_high_competition(self):
        assert adjust_threshold_for_competition(70, 80) == 85
        assert adjust_threshold_for_competition(70, 60) == 80

    def test_adjust_threshold_low_competition(self):
        assert adjust_threshold_for_competition(70, 20) == 60

    def test_adjust_threshold_bounds(self):
        assert adjust_threshold_for_competition(90, 80) <= 100
        assert adjust_threshold_for_competition(50, 20) >= 50

    def test_adjust_threshold_mid(self):
        assert adjust_threshold_for_competition(70, 45) == 75

    def test_competitiveness_saturated(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=90),
            applicant_count=500,
            remote=True,
            location="San Francisco, CA",
        )
        assert result['competitiveness_score'] >= 70
        assert result['recommendation'] in ('apply_early', 'consider_skip')

    def test_competitiveness_fresh_low_competition(self):
        result = score_competitiveness(
            posted_at=timezone.now(),
            remote=False,
            location="Small Town, USA",
            company_size="startup",
        )
        assert result['competitiveness_score'] < 40
        assert result['recommendation'] == 'apply_soon'


class TestPipelineIntegration:
    def test_full_salary_throttle_flow(self):
        throttle = compute_throttle(140000, 190000, 150000, 200000)
        assert throttle['throttle_factor'] >= 0.7
        bid = compute_bid_score(80, throttle['throttle_factor'], 70, 60)
        assert 50 <= bid <= 100

    def test_full_competitive_adjustment_flow(self):
        comp = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=30),
            applicant_count=100,
            remote=True,
            location="San Francisco, CA",
            company_size="large",
        )
        assert comp['competitiveness_score'] > 30
        adjusted = adjust_threshold_for_competition(70, comp['competitiveness_score'])
        assert adjusted >= 70

    def test_throttle_with_competitive_overlap(self):
        throttle = compute_throttle(120000, 160000, 110000, 140000)
        assert throttle['throttle_factor'] >= 0.6
        comp = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=3),
            remote=False,
            location="Denver, CO",
            company_size="medium",
        )
        assert comp['competitiveness_score'] < 50
        assert comp['recommendation'] in ('apply_soon', 'apply_now')

    def test_bid_score_with_low_fit(self):
        throttle = compute_throttle(140000, 190000, 80000, 100000)
        bid = compute_bid_score(50, throttle['throttle_factor'], 40, 30)
        assert bid < 50

    def test_edge_case_no_salary_no_date(self):
        throttle = compute_throttle(None, None, None, None)
        assert throttle['throttle_factor'] == 1.0
        comp = score_competitiveness(posted_at=None, applicant_count=None)
        assert comp['competitiveness_score'] == 30

    def test_competitive_estimate_with_reported_count(self):
        assert estimate_applicant_count(timezone.now() - timedelta(days=30), reported_count=50) == 50
        # reported_count=0 is ambiguous (0 applicants vs no data), falls through to estimate
        estimated = estimate_applicant_count(timezone.now() - timedelta(days=30), reported_count=0)
        assert estimated > 0

    def test_wilson_interval_consistency(self):
        results = []
        for successes in range(11):
            lo, hi, rate = _wilson_score_interval(successes, 10, 1.96)
            results.append((successes, rate, lo, hi))
        for i in range(1, len(results)):
            assert results[i][1] >= results[i - 1][1]


class TestEdgeCases:
    def test_competitiveness_future_date(self):
        result = score_competitiveness(posted_at=timezone.now() + timedelta(days=7))
        assert 0 <= result['competitiveness_score'] <= 100
        assert result['estimated_applicants'] == 0

    def test_competitiveness_very_old(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=200),
            remote=True,
            location="San Francisco, CA",
            company_size="enterprise",
        )
        assert result['competitiveness_score'] >= 70
        assert result['estimated_applicants'] == 500

    def test_competitiveness_no_company_size(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=5),
            company_size=None,
            location="Rural, USA",
        )
        assert 0 <= result['competitiveness_score'] <= 100

    def test_estimate_applicant_count_very_fresh(self):
        assert estimate_applicant_count(timezone.now() - timedelta(hours=1)) == 0

    def test_estimate_applicant_count_capped(self):
        capped = estimate_applicant_count(timezone.now() - timedelta(days=200))
        assert capped == 500

    def test_throttle_edge_near_zero(self):
        result = compute_throttle(100000, 150000, 1, 1000)
        assert result['throttle_factor'] < 0.1
        assert result['bid_score'] < 10

    def test_throttle_overlap_exact_match(self):
        result = compute_throttle(150000, 200000, 150000, 200000)
        assert result['throttle_factor'] >= 0.9
        assert result['bid_score'] >= 80

    def test_bid_score_perfect(self):
        score = compute_bid_score(100, 1.0, 100, 100)
        assert score == 100

    def test_bid_score_zero(self):
        score = compute_bid_score(0, 0.0, 0, 0)
        assert score == 0

    def test_wilson_interval_high_confidence(self):
        lo, hi, rate = _wilson_score_interval(95, 100, 2.576)
        assert lo > 0.8
        assert hi > 0.9
        assert rate == 0.95

    def test_salary_throttle_mixed_periods(self):
        result = compute_throttle(
            target_salary_min=5000, target_salary_max=8000,
            job_salary_min=60, job_salary_max=80,
            job_salary_period='hourly',
        )
        # Job is 60-80/hr = 124,800-166,400/yr, target is 5k-8k/mo = 60k-96k/yr
        # Job is well above target (166k > 96k * 1.5)
        assert result['throttle_factor'] <= 0.6

    def test_competitiveness_unknown_location(self):
        result = score_competitiveness(
            posted_at=timezone.now() - timedelta(days=10),
            location=None,
        )
        assert 0 <= result['competitiveness_score'] <= 100
        assert result['estimated_applicants'] > 0
