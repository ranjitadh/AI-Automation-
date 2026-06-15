JOB_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "skills_match": {"type": "integer", "minimum": 0, "maximum": 100},
        "experience_match": {"type": "integer", "minimum": 0, "maximum": 100},
        "location_match": {"type": "integer", "minimum": 0, "maximum": 100},
        "salary_fit": {"type": "integer", "minimum": 0, "maximum": 100},
        "seniority_match": {"type": "integer", "minimum": 0, "maximum": 100},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "matching_skills": {"type": "array", "items": {"type": "string"}},
        "key_requirements": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string", "enum": ["strong_apply", "apply", "consider", "skip"]},
        "summary": {"type": "string"},
    },
    "required": ["fit_score", "skills_match", "recommendation", "summary"],
}

RESUME_OPTIMIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "missing_keywords": {"type": "array", "items": {"type": "string"}},
        "ats_score_current": {"type": "integer", "minimum": 0, "maximum": 100},
        "ats_score_estimated": {"type": "integer", "minimum": 0, "maximum": 100},
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "optimized_bullets": {"type": "array", "items": {"type": "string"}},
        "summary_rewrite": {"type": "string"},
        "changes": {"type": "object"},
    },
    "required": ["ats_score_current", "ats_score_estimated", "suggestions"],
}

SKILL_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string"}},
        "technologies": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
        "soft_skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["skills"],
}

COVER_LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "salutation": {"type": "string"},
        "body": {"type": "string"},
        "closing": {"type": "string"},
    },
    "required": ["subject", "body", "closing"],
}

INTERVIEW_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "ideal_answer": {"type": "string"},
                    "star_response": {"type": "string"},
                },
                "required": ["question", "category", "ideal_answer"],
            },
        },
    },
    "required": ["questions"],
}

CAREER_AGENT_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["apply", "skip", "research", "prepare", "wait"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
        "recommended_resume": {"type": "string"},
        "needs_cover_letter": {"type": "boolean"},
        "priority_score": {"type": "integer", "minimum": 0, "maximum": 100},
    },
    "required": ["action", "confidence", "reasoning", "priority_score"],
}

ATS_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "ats_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "keyword_match_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "formatting_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "section_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "missing_sections": {"type": "array", "items": {"type": "string"}},
        "missing_keywords": {"type": "array", "items": {"type": "string"}},
        "suggested_improvements": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ats_score", "keyword_match_rate", "missing_keywords"],
}

APPLICATION_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["apply", "reject", "review", "queue"]},
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "skill_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "experience_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "seniority_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "industry_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "salary_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "location_match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "overqualification_risk": {"type": "string", "enum": ["none", "low", "medium", "high"]},
        "underqualification_risk": {"type": "string", "enum": ["none", "low", "medium", "high"]},
        "auto_reject_reason": {"type": "string"},
        "reasoning": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["decision", "fit_score", "reasoning", "confidence"],
}

RESUME_ADAPTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "adapted_summary": {"type": "string"},
        "adapted_experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["company", "title", "bullets"],
            },
        },
        "adapted_skills": {"type": "array", "items": {"type": "string"}},
        "skill_emphasis": {"type": "string", "enum": ["maintain", "downgrade", "upgrade", "rephrase"]},
        "seniority_presentation": {"type": "string", "enum": ["full", "reduced_leadership", "technical_focus", "balanced"]},
        "changes_summary": {"type": "object"},
        "ats_score_estimate": {"type": "integer", "minimum": 0, "maximum": 100},
    },
    "required": ["adapted_summary", "adapted_experience", "adapted_skills", "changes_summary"],
}

HUMANIZED_COVER_LETTER_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "salutation": {"type": "string"},
        "body_paragraphs": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
        "closing": {"type": "string"},
        "full_text": {"type": "string"},
        "word_count": {"type": "integer", "minimum": 150, "maximum": 300},
        "human_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["full_text", "body_paragraphs", "closing"],
}

SCREENING_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "consistent_with_resume": {"type": "boolean"},
                },
                "required": ["question", "answer", "consistent_with_resume"],
            },
        },
    },
    "required": ["answers"],
}

APPLICATION_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid": {"type": "boolean"},
        "checks": {
            "type": "object",
            "properties": {
                "resume_exists": {"type": "boolean"},
                "cover_letter_exists": {"type": "boolean"},
                "fit_score_acceptable": {"type": "boolean"},
                "answers_generated": {"type": "boolean"},
                "profile_consistent": {"type": "boolean"},
                "no_contradictions": {"type": "boolean"},
                "ats_score_adequate": {"type": "boolean"},
            },
            "required": ["resume_exists", "cover_letter_exists", "fit_score_acceptable"],
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
        "blockers": {"type": "array", "items": {"type": "string"}},
        "decision": {"type": "string", "enum": ["submit", "queue_for_review", "block"]},
    },
    "required": ["is_valid", "checks", "decision"],
}

LEARNING_OUTCOME_SCHEMA = {
    "type": "object",
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "category": {"type": "string", "enum": ["resume", "skills", "industry", "salary", "title", "seniority", "location", "timing", "cover_letter", "other"]},
                    "insight": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "actionable_advice": {"type": "string"},
                },
                "required": ["pattern", "category", "insight"],
            },
        },
        "resume_variant_performance": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "variant_key": {"type": "string"},
                    "interview_rate": {"type": "number", "minimum": 0, "maximum": 1},
                    "sample_size": {"type": "integer"},
                },
            },
        },
        "best_performing_skills": {"type": "array", "items": {"type": "string"}},
        "best_industries": {"type": "array", "items": {"type": "string"}},
        "optimal_salary_range": {"type": "object"},
    },
    "required": ["patterns"],
}

EXPERIENCE_CALIBRATION_SCHEMA = {
    "type": "object",
    "properties": {
        "calibration_type": {"type": "string", "enum": ["downgrade", "upgrade", "maintain"]},
        "reason": {"type": "string"},
        "seniority_gap": {"type": "string", "enum": ["massive_overqualified", "slight_overqualified", "match", "slight_underqualified", "massive_underqualified"]},
        "changes": {
            "type": "object",
            "properties": {
                "downgrade_titles": {"type": "boolean"},
                "reduce_leadership_emphasis": {"type": "boolean"},
                "increase_technical_emphasis": {"type": "boolean"},
                "highlight_transferable_skills": {"type": "boolean"},
                "reorder_experience": {"type": "boolean"},
            },
        },
        "presentation_guidance": {"type": "string"},
    },
    "required": ["calibration_type", "reason", "seniority_gap"],
}

RECRUITER_SIMULATION_SCHEMA = {
    "type": "object",
    "properties": {
        "interview_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "rejection_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "ats_probability": {"type": "number", "minimum": 0, "maximum": 1},
        "hiring_manager_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "recruiter_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "technical_interviewer_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "perspectives": {
            "type": "object",
            "properties": {
                "hr_recruiter": {"type": "object"},
                "hiring_manager": {"type": "object"},
                "ats": {"type": "object"},
                "technical_interviewer": {"type": "object"},
            },
        },
    },
    "required": ["interview_probability", "rejection_probability"],
}

APPLICATION_QUALITY_SCHEMA = {
    "type": "object",
    "properties": {
        "application_quality_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "application_authenticity_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "humanity_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "ai_detection_risk": {"type": "object"},
        "overqualification_risk": {"type": "object"},
        "underqualification_risk": {"type": "object"},
        "submission_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "should_submit": {"type": "boolean"},
        "can_auto_submit": {"type": "boolean"},
    },
    "required": ["application_quality_score", "submission_confidence", "should_submit"],
}

INTERVIEW_MAXIMIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "has_data": {"type": "boolean"},
        "interview_rate": {"type": "number"},
        "interviews": {"type": "integer"},
        "rejections": {"type": "integer"},
        "total_applications": {"type": "integer"},
        "best_performing_industries": {"type": "array"},
        "best_performing_titles": {"type": "array"},
        "best_performing_skills": {"type": "array"},
        "best_performing_resume_versions": {"type": "array"},
        "optimal_salary_range": {"type": "object"},
        "optimal_company_size": {"type": "object"},
        "best_locations": {"type": "array"},
        "top_success_patterns": {"type": "array"},
    },
    "required": ["has_data", "interview_rate"],
}

ATS_OPTIMIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_ats_compatibility": {"type": "number"},
        "platform_scores": {"type": "array"},
        "weakest_platform": {"type": "string"},
        "weakest_score": {"type": "integer"},
        "strongest_platform": {"type": "string"},
        "strongest_score": {"type": "integer"},
        "priority_improvements": {"type": "array"},
    },
    "required": ["overall_ats_compatibility", "platform_scores"],
}

CONSISTENCY_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "is_consistent": {"type": "boolean"},
        "can_submit": {"type": "boolean"},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "blockers": {"type": "array", "items": {"type": "string"}},
        "checks_passed": {
            "type": "object",
            "properties": {
                "resume_valid": {"type": "boolean"},
                "cover_letter_consistent": {"type": "boolean"},
                "answers_consistent": {"type": "boolean"},
                "profile_complete": {"type": "boolean"},
                "job_aligned": {"type": "boolean"},
            },
        },
    },
    "required": ["is_consistent", "can_submit", "contradictions"],
}

TASK_SCHEMAS = {
    'job_parsing': SKILL_EXTRACTION_SCHEMA,
    'skill_extraction': SKILL_EXTRACTION_SCHEMA,
    'ats_analysis': ATS_ANALYSIS_SCHEMA,
    'resume_optimization': RESUME_OPTIMIZATION_SCHEMA,
    'cover_letter': COVER_LETTER_SCHEMA,
    'fit_scoring': JOB_ANALYSIS_SCHEMA,
    'career_agent_reasoning': CAREER_AGENT_DECISION_SCHEMA,
    'interview_preparation': INTERVIEW_QUESTION_SCHEMA,
    'application_decision': APPLICATION_DECISION_SCHEMA,
    'resume_adaptation': RESUME_ADAPTATION_SCHEMA,
    'humanized_cover_letter': HUMANIZED_COVER_LETTER_SCHEMA,
    'screening_answer': SCREENING_ANSWER_SCHEMA,
    'application_validation': APPLICATION_VALIDATION_SCHEMA,
    'learning_outcome': LEARNING_OUTCOME_SCHEMA,
    'experience_calibration': EXPERIENCE_CALIBRATION_SCHEMA,
    'consistency_check': CONSISTENCY_CHECK_SCHEMA,
    'recruiter_simulation': RECRUITER_SIMULATION_SCHEMA,
    'application_quality': APPLICATION_QUALITY_SCHEMA,
    'interview_maximization': INTERVIEW_MAXIMIZATION_SCHEMA,
    'ats_optimization': ATS_OPTIMIZATION_SCHEMA,
}
