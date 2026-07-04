import pytest
from django.test import TestCase
from apps.ai.resume_adaptation_engine import (
    verify_resume_truthfulness,
    _normalize_key,
    _normalize_date,
)


class NormalizeKeyTests(TestCase):
    def test_normalize_company_title(self):
        result = _normalize_key("Acme Corp", "Senior Engineer")
        self.assertIn("acme", result)
        self.assertIn("senior", result)

    def test_normalize_strips_suffixes(self):
        result = _normalize_key("Acme Inc", "Dev")
        self.assertNotIn("inc", result)

    def test_normalize_senior_variants(self):
        result = _normalize_key("Acme", "Sr. Engineer")
        result2 = _normalize_key("Acme", "Senior Engineer")
        self.assertEqual(result, result2)


class NormalizeDateTests(TestCase):
    def test_normalize_iso_date(self):
        self.assertEqual(_normalize_date("2021-06"), "2021-06")

    def test_normalize_month_name(self):
        self.assertIn("06", _normalize_date("June 2021"))

    def test_normalize_empty(self):
        self.assertEqual(_normalize_date(""), "")


class TruthfulnessVerificationTests(TestCase):
    def test_identical_experience(self):
        original = [
            {"company": "Acme Inc", "title": "Developer", "start_date": "2020-01", "end_date": "2023-01"},
        ]
        adapted = [
            {"company": "Acme Inc", "title": "Developer", "start_date": "2020-01", "end_date": "2023-01",
             "bullets": ["Wrote code"]},
        ]
        issues = verify_resume_truthfulness(original, adapted)
        self.assertEqual(len(issues), 0)

    def test_fabricated_company(self):
        original = [
            {"company": "Acme Inc", "title": "Developer"},
        ]
        adapted = [
            {"company": "Acme Inc", "title": "Developer", "bullets": ["Wrote code"]},
            {"company": "Fake Corp", "title": "CTO", "bullets": ["Led team"]},
        ]
        issues = verify_resume_truthfulness(original, adapted)
        self.assertTrue(any('FABRICATED' in issue for issue in issues))

    def test_date_mismatch(self):
        original = [
            {"company": "Acme Inc", "title": "Developer", "start_date": "2020-01", "end_date": "2023-01"},
        ]
        adapted = [
            {"company": "Acme Inc", "title": "Developer", "start_date": "2019-01", "end_date": "2023-01",
             "bullets": ["Wrote code"]},
        ]
        issues = verify_resume_truthfulness(original, adapted)
        self.assertTrue(any('DATE MISMATCH' in issue for issue in issues))

    def test_missing_experience(self):
        original = [
            {"company": "Acme Inc", "title": "Developer"},
            {"company": "Beta Corp", "title": "Senior Dev"},
        ]
        adapted = [
            {"company": "Acme Inc", "title": "Developer", "bullets": ["Wrote code"]},
        ]
        issues = verify_resume_truthfulness(original, adapted)
        self.assertTrue(any('MISSING' in issue for issue in issues))

    def test_empty_original(self):
        issues = verify_resume_truthfulness([], [{"company": "Fake", "title": "Dev", "bullets": []}])
        self.assertTrue(len(issues) > 0)
