import pytest
from django.test import TestCase
from apps.ai.consistency_engine import (
    verify_application_consistency,
    _check_resume_consistency,
    _check_cover_letter_consistency,
    _check_screening_answer_consistency,
    _check_profile_completeness,
    _check_job_consistency,
    _compute_years_from_experience,
    _extract_years,
)


class YearsExtractionTests(TestCase):
    def test_extract_years_from_text(self):
        self.assertEqual(_extract_years("5 years of experience"), 5.0)

    def test_extract_years_with_plus(self):
        self.assertEqual(_extract_years("5+ years experience"), 5.0)

    def test_extract_years_no_match(self):
        self.assertIsNone(_extract_years("Some text without years"))


class ComputeYearsTests(TestCase):
    def test_compute_years_from_experience(self):
        exp = [
            {"start_date": "2018-01", "end_date": "2023-01"},
            {"start_date": "2016-01", "end_date": "2018-01"},
        ]
        result = _compute_years_from_experience(exp)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 7.0, delta=0.5)

    def test_compute_years_with_present(self):
        exp = [
            {"start_date": "2020-01", "end_date": "Present"},
        ]
        result = _compute_years_from_experience(exp)
        self.assertIsNotNone(result)
        self.assertGreater(result, 4.0)

    def test_compute_years_empty(self):
        self.assertIsNone(_compute_years_from_experience([]))


class ResumeConsistencyTests(TestCase):
    def test_valid_resume(self):
        result = _check_resume_consistency(
            {"experience": [{"company": "A", "title": "Dev"}], "skills": ["Python"], "years_of_experience": 5},
            {},
        )
        self.assertTrue(result['resume_valid'])

    def test_empty_resume(self):
        result = _check_resume_consistency({}, {})
        self.assertFalse(result['resume_valid'])

    def test_years_mismatch(self):
        result = _check_resume_consistency(
            {
                "experience": [{"start_date": "2018", "end_date": "2020"}],
                "years_of_experience": 20,
            },
            {},
        )
        self.assertTrue(len(result.get('contradictions', [])) > 0)


class CoverLetterConsistencyTests(TestCase):
    def test_cover_letter_mentions_company(self):
        result = _check_cover_letter_consistency(
            "I want to work at Acme Corp as a Software Engineer. I have Python skills.",
            {"skills": ["Python"], "summary": "Engineer with Python experience"},
            {},
            {"company": "Acme Corp", "title": "Software Engineer"},
        )
        self.assertTrue(result['consistent'])

    def test_cover_letter_missing_company(self):
        result = _check_cover_letter_consistency(
            "I want to work at your company.",
            {"skills": ["Python"], "summary": "Engineer with Python experience"},
            {},
            {"company": "Acme Corp", "title": "Software Engineer"},
        )
        self.assertFalse(result['consistent'])

    def test_cover_letter_too_short(self):
        result = _check_cover_letter_consistency("Hi", {}, {}, {})
        self.assertFalse(result['consistent'])


class ScreeningAnswerConsistencyTests(TestCase):
    def test_years_answer_matches(self):
        result = _check_screening_answer_consistency(
            [{"question": "How many years of experience?", "answer": "5 years", "confidence": 0.9}],
            {"years_of_experience": 5, "skills": [], "experience": [], "work_authorization": ""},
            {"goals": {}},
        )
        self.assertTrue(result['consistent'])

    def test_years_answer_mismatch(self):
        result = _check_screening_answer_consistency(
            [{"question": "How many years of experience?", "answer": "15 years", "confidence": 0.9}],
            {"years_of_experience": 3, "skills": [], "experience": [], "work_authorization": ""},
            {"goals": {}},
        )
        self.assertFalse(len(result.get('contradictions', [])) == 0)

    def test_low_confidence_flagged(self):
        result = _check_screening_answer_consistency(
            [{"question": "Do you know Python?", "answer": "Yes", "confidence": 0.1}],
            {"years_of_experience": 5, "skills": ["Python"], "experience": [], "work_authorization": ""},
            {"goals": {}},
        )
        self.assertTrue(len(result.get('contradictions', [])) > 0)


class ProfileCompletenessTests(TestCase):
    def test_complete_profile(self):
        result = _check_profile_completeness({
            "resume": {"skills": ["Python"], "experience": [{"company": "A"}], "years_of_experience": 5},
            "goals": {"target_titles": ["Engineer"], "work_authorization": "US Citizen"},
        })
        self.assertTrue(result['complete'])

    def test_missing_resume(self):
        result = _check_profile_completeness({})
        self.assertFalse(result['complete'])
        self.assertTrue(len(result.get('blockers', [])) > 0)

    def test_missing_skills_warning(self):
        result = _check_profile_completeness({
            "resume": {"experience": [{"company": "A"}], "years_of_experience": 5},
            "goals": {"target_titles": ["Engineer"], "work_authorization": "US Citizen"},
        })
        self.assertTrue(len(result.get('warnings', [])) > 0)


class JobConsistencyTests(TestCase):
    def test_salary_aligned(self):
        result = _check_job_consistency(
            {"resume": {"skills": ["Python"]}, "goals": {"target_salary_min": 80000, "target_salary_max": 120000}},
            {"salary_min": 90000, "salary_max": 110000, "requirements": ["Python"]},
        )
        self.assertTrue(result['aligned'])

    def test_salary_mismatch(self):
        result = _check_job_consistency(
            {"resume": {"skills": ["Python"]}, "goals": {"target_salary_min": 100000, "target_salary_max": 150000}},
            {"salary_min": 40000, "salary_max": 60000, "requirements": ["Python"]},
        )
        self.assertTrue(len(result.get('warnings', [])) > 0)


class FullConsistencyCheckTests(TestCase):
    def test_consistent_application(self):
        result = verify_application_consistency(
            resume_data={
                "skills": ["Python", "Django"],
                "experience": [{"company": "Acme", "title": "Dev", "start_date": "2020", "end_date": "2023"}],
                "years_of_experience": 3,
                "summary": "Python developer with Django experience",
                "work_authorization": "US Citizen",
            },
            cover_letter_text="I want to work at Acme Corp as a Software Engineer. I use Python and Django daily.",
            screening_answers=[
                {"question": "Years of experience?", "answer": "3 years", "confidence": 0.9},
            ],
            profile_data={
                "goals": {
                    "target_titles": ["Software Engineer"],
                    "target_salary_min": 80000,
                    "target_salary_max": 120000,
                    "work_authorization": "US Citizen",
                    "remote_preference": "any",
                },
            },
            job_data={
                "company": "Acme Corp",
                "title": "Software Engineer",
                "location": "Remote",
                "salary_min": 90000,
                "salary_max": 110000,
                "requirements": ["Python"],
            },
        )
        self.assertTrue(result['is_consistent'])
        self.assertTrue(result['can_submit'])

    def test_contradictory_application(self):
        result = verify_application_consistency(
            resume_data={
                "skills": ["Python"],
                "experience": [{"company": "Acme", "title": "Dev", "start_date": "2020", "end_date": "2023"}],
                "years_of_experience": 3,
                "summary": "Developer",
                "work_authorization": "US Citizen",
            },
            cover_letter_text="Short letter",
            screening_answers=[
                {"question": "Years of experience?", "answer": "15 years", "confidence": 0.9},
            ],
            profile_data={
                "goals": {
                    "target_titles": ["Engineer"],
                    "work_authorization": "US Citizen",
                },
            },
            job_data={
                "company": "Acme Corp",
                "title": "Software Engineer",
                "salary_min": 90000,
                "salary_max": 110000,
                "requirements": ["Python"],
            },
        )
        self.assertFalse(result['is_consistent'])
