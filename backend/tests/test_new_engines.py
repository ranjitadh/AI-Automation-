import pytest
from datetime import datetime, timedelta

from apps.ai.recruiter_simulation_engine import (
    simulate_recruiter_perspectives,
    _simulate_hr_recruiter,
    _simulate_hiring_manager,
    _simulate_ats,
    _simulate_technical_interviewer,
    _combine_scores,
    _looks_ai_generated,
    _compute_experience_years,
)

from apps.ai.application_quality_engine import (
    evaluate_application_quality,
    _score_application_quality,
    _score_authenticity,
    _score_humanity,
    _assess_ai_detection_risk,
    _assess_overqualification_risk,
    _assess_underqualification_risk,
    _compute_submission_confidence,
)

from apps.ai.interview_maximization_engine import (
    _normalize_title,
    _empty_result,
)

from apps.ai.ats_optimization_engine import (
    evaluate_ats_compatibility,
    _score_for_platform,
    _has_html_formatting,
    ATS_PLATFORMS,
)


SAMPLE_RESUME = {
    "summary": "Experienced software engineer with 8 years building scalable systems",
    "skills": ["Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis", "GraphQL", "CI/CD"],
    "years_of_experience": 8,
    "experience": [
        {"company": "Tech Corp", "title": "Senior Engineer", "start_date": "2020-01", "end_date": "Present",
         "bullets": ["Built microservices handling 10K req/s", "Led team of 5 engineers"]},
        {"company": "Startup Inc", "title": "Software Engineer", "start_date": "2017-03", "end_date": "2019-12",
         "bullets": ["Developed REST APIs", "Reduced deployment time by 60%"]},
        {"company": "Web Agency", "title": "Junior Developer", "start_date": "2015-06", "end_date": "2017-02",
         "bullets": ["Built client websites", "Implemented CI/CD pipeline"]},
    ],
    "work_authorization": "US Citizen",
}

SAMPLE_JOB = {
    "title": "Senior Software Engineer",
    "company": "Target Company",
    "company_name": "Target Company",
    "description": "We're looking for a senior engineer to build scalable backend services",
    "required_skills": ["Python", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis"],
    "technologies": ["Python", "AWS", "Docker"],
    "tools": ["Git", "Jira"],
    "years_experience_required": 5,
    "seniority_level": "senior",
    "location": "San Francisco, CA",
    "salary_min": 150000,
    "salary_max": 200000,
    "company_industry": "saas",
    "requirements": ["Python", "AWS", "Docker", "Kubernetes"],
    "responsibilities": ["Build APIs", "Design systems"],
}

SAMPLE_COVER_LETTER = (
    "I'm interested in the Senior Software Engineer role at Target Company. "
    "I've spent the last 8 years building scalable systems, most recently at Tech Corp "
    "where I led a team of 5 engineers building microservices handling 10K requests per second. "
    "My experience with Python, AWS, Docker, and Kubernetes maps well to what you're looking for. "
    "I'd love to discuss how I can contribute to your team. "
    "Thanks for reviewing my application."
)

SAMPLE_ANSWERS = [
    {"question": "How many years of experience?", "answer": "8 years", "confidence": 0.9, "consistent_with_resume": True},
    {"question": "What is your salary expectation?", "answer": "160000", "confidence": 0.8, "consistent_with_resume": True},
    {"question": "Are you authorized to work?", "answer": "Yes, US Citizen", "confidence": 1.0, "consistent_with_resume": True},
]

SAMPLE_PROFILE = {
    "skills": ["Python", "JavaScript", "React", "AWS", "Docker"],
    "goals": {
        "target_titles": ["Senior Engineer", "Staff Engineer"],
        "target_salary_min": 140000,
        "target_salary_max": 200000,
        "remote_preference": "hybrid",
        "work_authorization": "US Citizen",
        "target_locations": ["San Francisco", "Remote"],
        "open_to_relocation": True,
    },
}


class TestRecruiterSimulationEngine:
    def test_simulate_hr_recruiter_strong(self):
        score, reasoning = _simulate_hr_recruiter(SAMPLE_RESUME, SAMPLE_COVER_LETTER, SAMPLE_PROFILE)
        assert 0 <= score <= 100
        assert score >= 70

    def test_simulate_hr_recruiter_no_resume(self):
        score, reasoning = _simulate_hr_recruiter({}, "", {})
        assert score == 0

    def test_simulate_hiring_manager_good_match(self):
        score, reasoning = _simulate_hiring_manager(SAMPLE_RESUME, SAMPLE_JOB, SAMPLE_ANSWERS)
        assert 0 <= score <= 100
        assert score >= 70

    def test_simulate_hiring_manager_weak_match(self):
        weak_resume = {**SAMPLE_RESUME, "skills": ["Cobol", "Fortran"], "years_of_experience": 1}
        score, reasoning = _simulate_hiring_manager(weak_resume, SAMPLE_JOB, [])
        assert score < 60

    def test_simulate_ats_good_match(self):
        result = _simulate_ats(SAMPLE_RESUME, SAMPLE_JOB)
        assert 0 <= result["ats_score"] <= 100
        assert result["keyword_match"] > 0

    def test_simulate_ats_no_skills(self):
        no_skills = {**SAMPLE_RESUME, "skills": [], "summary": ""}
        result = _simulate_ats(no_skills, SAMPLE_JOB)
        assert "Skills section" in result["missing_sections"]

    def test_simulate_technical_interviewer_good(self):
        score, reasoning = _simulate_technical_interviewer(SAMPLE_RESUME, SAMPLE_JOB)
        assert 0 <= score <= 100

    def test_combine_scores(self):
        result = _combine_scores(80, 75, 70, 85)
        assert 0 <= result["interview_probability"] <= 1
        assert 0 <= result["rejection_probability"] <= 1
        assert result["interview_probability"] + result["rejection_probability"] == pytest.approx(1.0, 0.01)
        assert 0 <= result["confidence"] <= 1

    def test_full_simulation_returns_all_fields(self):
        result = simulate_recruiter_perspectives(SAMPLE_RESUME, SAMPLE_COVER_LETTER, SAMPLE_ANSWERS, SAMPLE_PROFILE, SAMPLE_JOB)
        required = ["interview_probability", "rejection_probability", "ats_probability",
                     "hiring_manager_score", "recruiter_score", "technical_interviewer_score",
                     "confidence_score", "perspectives", "combined"]
        for field in required:
            assert field in result, f"Missing field: {field}"
        assert "hr_recruiter" in result["perspectives"]
        assert "hiring_manager" in result["perspectives"]
        assert "ats" in result["perspectives"]
        assert "technical_interviewer" in result["perspectives"]

    def test_looks_ai_generated_positive(self):
        ai_text = "I am writing to apply for this position. I am excited to join your team. I am confident that my skills align perfectly with your requirements."
        assert _looks_ai_generated(ai_text)

    def test_looks_ai_generated_negative(self):
        natural = "I've been following Target Company for a while. The work you're doing in the AI space is really interesting. I'd love to chat about how my background fits."
        assert not _looks_ai_generated(natural)


class TestApplicationQualityEngine:
    def test_evaluate_full_quality(self):
        result = evaluate_application_quality(SAMPLE_RESUME, SAMPLE_COVER_LETTER, SAMPLE_ANSWERS, SAMPLE_PROFILE, SAMPLE_JOB)
        assert 0 <= result["application_quality_score"] <= 100
        assert 0 <= result["application_authenticity_score"] <= 100
        assert 0 <= result["humanity_score"] <= 100
        assert 0 <= result["submission_confidence"] <= 1
        assert isinstance(result["should_submit"], bool)
        assert isinstance(result["can_auto_submit"], bool)

    def test_quality_score_no_cover_letter(self):
        score, factors = _score_application_quality(SAMPLE_RESUME, "", SAMPLE_ANSWERS, SAMPLE_PROFILE, SAMPLE_JOB)
        assert score == 80
        assert "No cover letter" in factors

    def test_authenticity_score_generic_phrases(self):
        bad_cl = "I am writing to apply for this position. I am excited to join your team. I am confident that my skills align perfectly."
        score, factors = _score_authenticity(SAMPLE_RESUME, bad_cl, [], SAMPLE_PROFILE)
        assert score < 80

    def test_humanity_score_natural(self):
        score, factors = _score_humanity(SAMPLE_COVER_LETTER)
        assert score > 30

    def test_humanity_score_ai_text(self):
        ai_text = "I am writing to apply for this role. I am excited to bring my proven track record. I am confident that my synergy and leverage will optimize your operations."
        score, factors = _score_humanity(ai_text)
        assert score < 70

    def test_ai_detection_risk(self):
        result = _assess_ai_detection_risk(SAMPLE_RESUME, SAMPLE_COVER_LETTER, SAMPLE_ANSWERS)
        assert result["level"] in ("none", "low", "medium", "high")
        assert 0 <= result["risk_percentage"] <= 100

    def test_ai_detection_risk_high(self):
        ai_cl = "I am writing to apply for this position. I am excited to join your team. I am confident that my skills align perfectly. Please find attached my resume. I look forward to hearing from you."
        result = _assess_ai_detection_risk(SAMPLE_RESUME, ai_cl, [])
        assert result["severity"] >= 2

    def test_overqualification_risk(self):
        junior_job = {**SAMPLE_JOB, "years_experience_required": 2}
        result = _assess_overqualification_risk(SAMPLE_RESUME, junior_job)
        assert result["risk"] in ("none", "low", "medium", "high")

    def test_underqualification_risk(self):
        senior_job = {**SAMPLE_JOB, "years_experience_required": 15, "required_skills": ["Kubernetes", "TensorFlow", "PyTorch", "Spark", "Kafka", "Cassandra"]}
        result = _assess_underqualification_risk(SAMPLE_RESUME, senior_job)
        assert result["risk"] in ("none", "low", "medium", "high")

    def test_submission_confidence(self):
        conf = _compute_submission_confidence(80, 85, 75, {"level": "none", "severity": 0}, {"severity": 0}, {"severity": 0})
        assert 0 <= conf <= 1
        assert conf > 0.5

    def test_submission_confidence_penalized(self):
        conf = _compute_submission_confidence(60, 50, 40, {"level": "high", "severity": 6}, {"severity": 3}, {"severity": 3})
        assert conf < 0.6
        assert 0 <= conf <= 1


class TestATSOptimizationEngine:
    def test_evaluate_ats_compatibility(self):
        result = evaluate_ats_compatibility(SAMPLE_RESUME)
        assert 0 <= result["overall_ats_compatibility"] <= 100
        assert len(result["platform_scores"]) == len(ATS_PLATFORMS)
        assert result["weakest_platform"] is not None
        assert result["strongest_platform"] is not None

    def test_score_for_platform_returns_all_fields(self):
        platform = ATS_PLATFORMS[0]
        result = _score_for_platform(SAMPLE_RESUME, platform)
        assert 0 <= result["compatibility_score"] <= 100
        assert isinstance(result["strengths"], list)
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)

    def test_has_html_formatting(self):
        assert _has_html_formatting("Some <b>bold</b> text")
        assert not _has_html_formatting("Plain text")

    def test_all_platforms_have_required_fields(self):
        for p in ATS_PLATFORMS:
            assert "name" in p
            assert "domain" in p
            assert "max_field_length" in p
            assert "parsing_quality" in p


class TestInterviewMaximizationEngine:
    def test_normalize_title(self):
        assert "engineer" in _normalize_title("Senior Software Engineer")
        assert "engineer" in _normalize_title("Staff Engineer")
        assert "manager" in _normalize_title("Senior Product Manager")

    def test_empty_result(self):
        result = _empty_result("test message")
        assert result["has_data"] is False
        assert result["message"] == "test message"
        assert result["interview_rate"] == 0


class TestComputeExperienceYears:
    def test_compute_years(self):
        years = _compute_experience_years(SAMPLE_RESUME)
        assert years > 0
        assert isinstance(years, int)
