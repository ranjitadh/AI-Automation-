import json
import logging

from .gateway import generate
from .schemas import INTERVIEW_QUESTION_SCHEMA

logger = logging.getLogger(__name__)


def prepare_interview(job_data: dict, interview_type: str = 'technical') -> dict:
    system_prompt = (
        "You are an expert interview coach. Generate a comprehensive interview "
        "preparation guide including company summary, role analysis, likely questions, "
        "and STAR response frameworks."
    )
    user_prompt = json.dumps({
        "job": job_data,
        "interview_type": interview_type,
    })

    result = generate(
        task_type='interview_preparation',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=INTERVIEW_QUESTION_SCHEMA,
    )
    return result.get('parsed', result)


def generate_star_response(question: str, experience_context: dict = None) -> dict:
    system_prompt = (
        "You are an expert at crafting STAR (Situation, Task, Action, Result) "
        "responses for behavioral interview questions. Given the question and the "
        "candidate's experience, generate a compelling STAR response."
    )
    user_prompt = json.dumps({
        "question": question,
        "context": experience_context or {},
    })

    result = generate(
        task_type='interview_preparation',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    return result.get('parsed', result)
