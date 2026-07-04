import json
import logging

from .gateway import generate
from .schemas import TASK_SCHEMAS
from .models import PromptTemplate

logger = logging.getLogger(__name__)


def _get_prompt(task_type: str, prompt_name: str = None) -> dict:
    if prompt_name:
        tmpl = PromptTemplate.objects.filter(
            name=prompt_name, is_active=True
        ).order_by('-version').first()
        if tmpl:
            return {
                'system': tmpl.system_prompt,
                'template': tmpl.user_prompt_template or '',
                'schema': tmpl.response_schema or TASK_SCHEMAS.get(task_type),
            }
    return {
        'system': _DEFAULT_SYSTEM_PROMPTS.get(task_type, _DEFAULT_SYSTEM_PROMPTS['default']),
        'template': '',
        'schema': TASK_SCHEMAS.get(task_type),
    }


def ai_generate(task_type: str, user_message: str,
                prompt_name: str = None, **kwargs) -> dict:
    prompt = _get_prompt(task_type, prompt_name)
    schema = kwargs.pop('response_schema', None) or prompt['schema']

    user_prompt = user_message
    if prompt['template']:
        user_prompt = prompt['template'].format(message=user_message, **kwargs)

    return generate(
        task_type=task_type,
        system_prompt=prompt['system'],
        user_prompt=user_prompt,
        response_schema=schema,
        prompt_name=prompt_name or task_type,
        **kwargs,
    )


def analyze_job_fit(job_data: dict, resume_data: dict = None, **kwargs) -> dict:
    user_msg = json.dumps({
        "job": job_data,
        "resume": resume_data,
    })
    return ai_generate('fit_scoring', user_msg, **kwargs)


def optimize_resume(resume_text: str, job_description: str, **kwargs) -> dict:
    user_msg = json.dumps({
        "resume": resume_text,
        "job_description": job_description,
    })
    return ai_generate('resume_optimization', user_msg, **kwargs)


def generate_cover_letter(job_data: dict, resume_data: dict = None, style: str = 'medium', **kwargs) -> dict:
    user_msg = json.dumps({
        "job": job_data,
        "resume": resume_data,
        "style": style,
    })
    return ai_generate('cover_letter', user_msg, **kwargs)


def generate_interview_questions(job_data: dict, interview_type: str = 'technical', **kwargs) -> dict:
    user_msg = json.dumps({
        "job": job_data,
        "interview_type": interview_type,
    })
    return ai_generate('interview_preparation', user_msg, **kwargs)


def answer_question(question: str, context: dict = None, **kwargs) -> dict:
    user_msg = json.dumps({
        "question": question,
        "context": context or {},
    })
    return ai_generate('question_answering', user_msg, **kwargs)


_DEFAULT_SYSTEM_PROMPTS = {
    'fit_scoring': (
        "You are an expert job fit analyzer. Analyze the job and resume data provided "
        "and return a structured assessment of how well the candidate fits the role. "
        "Be objective and data-driven. Return scores out of 100."
    ),
    'resume_optimization': (
        "You are an expert ATS resume optimizer. Analyze the resume against the job "
        "description and provide specific optimization suggestions. Maximize ATS "
        "compatibility while keeping the resume truthful."
    ),
    'cover_letter': (
        "You are an expert cover letter writer. Write compelling, personalized cover "
        "letters that highlight relevant experience and enthusiasm for the role. "
        "Keep it professional and concise."
    ),
    'interview_preparation': (
        "You are an expert interview coach. Generate likely interview questions "
        "based on the job description, along with ideal answers and STAR framework "
        "responses."
    ),
    'question_answering': (
        "You are an expert career assistant. Answer job application questions "
        "professionally and persuasively, optimizing for the candidate being "
        "selected for interview."
    ),
    'skill_extraction': (
        "You are an expert skill extractor. Identify all technical skills, "
        "technologies, tools, and certifications mentioned in the text."
    ),
    'ats_analysis': (
        "You are an expert ATS compatibility analyst. Evaluate how well a resume "
        "will perform against Applicant Tracking Systems for a specific job."
    ),
    'job_parsing': (
        "You are an expert job description parser. Extract structured information "
        "from job postings including skills, requirements, responsibilities, and metadata."
    ),
    'default': (
        "You are an AI career agent assistant. Provide accurate, helpful responses."
    ),
}
