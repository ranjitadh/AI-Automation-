import json
import logging
from typing import Optional

from .gateway import generate
from .schemas import SCREENING_ANSWER_SCHEMA

logger = logging.getLogger(__name__)


def generate_screening_answers(questions: list, candidate_data: dict,
                               job_data: dict = None,
                               organization_id: str = None,
                               user_id: str = None) -> dict:
    system_prompt = (
        "You are an expert at answering job application screening questions. "
        "For each question, generate a truthful, consistent, and realistic answer "
        "based on the candidate's actual resume and profile. "
        "CRITICAL RULES: "
        "1. Every answer MUST be consistent with the candidate's resume. "
        "2. Never fabricate experience, skills, certifications, or credentials. "
        "3. Years of experience answers must match the candidate's actual years. "
        "4. Work authorization answers must match the candidate's actual status. "
        "5. Salary expectations must stay within the candidate's preferred range. "
        "6. Availability/start date must be realistic. "
        "7. Education answers must match actual degrees and institutions. "
        "8. If the question asks about a skill the candidate doesn't have, "
        "   answer honestly but highlight adjacent or transferable experience. "
        "9. Answers should be concise (1-3 sentences) unless the question requires more. "
        "10. Never contradict yourself across answers. "
        "Return a JSON with an 'answers' array where each item has: "
        "question, answer, confidence (0-1), consistent_with_resume (boolean)."
    )

    user_prompt = json.dumps({
        "candidate": {
            "summary": candidate_data.get('summary', ''),
            "skills": candidate_data.get('skills', [])[:30],
            "experience": [
                {
                    "company": e.get('company', ''),
                    "title": e.get('title', ''),
                    "years": f"{e.get('start_date', '')} - {e.get('end_date', 'Present')}",
                    "description": str(e.get('bullets', e.get('description', '')))[:500],
                }
                for e in (candidate_data.get('experience', []) or [])
            ],
            "education": [
                {
                    "degree": e.get('degree', e.get('name', '')),
                    "institution": e.get('institution', e.get('school', '')),
                    "year": e.get('year', e.get('graduation_year', '')),
                }
                for e in (candidate_data.get('education', []) or [])
            ],
            "years_of_experience": candidate_data.get('years_of_experience', 0),
            "work_authorization": candidate_data.get('work_authorization', ''),
            "seniority_level": candidate_data.get('seniority_level', ''),
            "certifications": candidate_data.get('certifications', []),
        },
        "job": {
            "title": job_data.get('title', ''),
            "company": job_data.get('company', ''),
            "seniority": job_data.get('seniority', ''),
        } if job_data else {},
        "questions": questions,
        "instructions": (
            "For years-of-experience questions: use the candidate's actual years_of_experience. "
            "For salary questions: use 'open to discussion' or a reasonable range. "
            "For work authorization: use the candidate's actual work_authorization. "
            "For 'Why do you want to work here?': reference the job title and company, "
            "mention specific aspects of the role or company that genuinely align "
            "with the candidate's background. Sound human, not like a form letter. "
            "For 'Tell us about yourself': write a 2-3 sentence professional summary "
            "based on the resume. "
            "For 'Do you have experience with X?': if yes, briefly describe the experience. "
            "If no, say 'I have adjacent experience with Y' or 'I am eager to apply my "
            "foundational knowledge in X to real projects.' Never flat-out lie."
        ),
    })

    result = generate(
        task_type='screening_answer',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=SCREENING_ANSWER_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def answer_single_question(question: str, candidate_data: dict,
                           job_data: dict = None,
                           organization_id: str = None,
                           user_id: str = None) -> dict:
    return generate_screening_answers(
        questions=[question],
        candidate_data=candidate_data,
        job_data=job_data,
        organization_id=organization_id,
        user_id=user_id,
    )
