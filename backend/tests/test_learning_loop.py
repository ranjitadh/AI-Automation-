import pytest
from django.test import TestCase
from apps.ai.matching_engine import _compute_learned_adjustments


class LearningAdjustmentTests(TestCase):
    def test_no_patterns_no_adjustment(self):
        result = _compute_learned_adjustments([], {"title": "Engineer"})
        self.assertEqual(result['total_adjustment'], 0)

    def test_missing_skills_penalty(self):
        patterns = [
            {"type": "failure_pattern", "key": "missing_skills_rejection", "confidence": 0.8, "value": {}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer"})
        self.assertLess(result['total_adjustment'], 0)

    def test_experience_gap_penalty(self):
        patterns = [
            {"type": "failure_pattern", "key": "experience_gap_rejection", "confidence": 0.7, "value": {}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer"})
        self.assertLess(result['total_adjustment'], 0)

    def test_success_pattern_bonus(self):
        patterns = [
            {"type": "success_pattern", "key": "interview_job1", "confidence": 0.8,
             "value": {"industry": "Tech"}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer", "company_industry": "Tech"})
        self.assertGreater(result['total_adjustment'], 0)

    def test_industry_preference_bonus(self):
        patterns = [
            {"type": "preference", "key": "industry_FinTech", "confidence": 0.9,
             "value": {"success_count": 3}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer", "company_industry": "FinTech"})
        self.assertGreater(result['total_adjustment'], 0)

    def test_adjustment_capped(self):
        patterns = [
            {"type": "failure_pattern", "key": "missing_skills_rejection", "confidence": 0.95, "value": {}},
            {"type": "failure_pattern", "key": "experience_gap_rejection", "confidence": 0.95, "value": {}},
            {"type": "failure_pattern", "key": "overqualified_rejection", "confidence": 0.95, "value": {}},
            {"type": "failure_pattern", "key": "salary_mismatch_rejection", "confidence": 0.95, "value": {}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer"})
        self.assertGreaterEqual(result['total_adjustment'], -30)
        self.assertLessEqual(result['total_adjustment'], 30)

    def test_low_confidence_ignored(self):
        patterns = [
            {"type": "failure_pattern", "key": "missing_skills_rejection", "confidence": 0.1, "value": {}},
        ]
        result = _compute_learned_adjustments(patterns, {"title": "Engineer"})
        self.assertEqual(result['total_adjustment'], 0)
