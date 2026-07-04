import json
import logging

from .gateway import generate
from .models import CareerMemory
from .schemas import JOB_ANALYSIS_SCHEMA, RESUME_OPTIMIZATION_SCHEMA

logger = logging.getLogger(__name__)


def analyze_fit(job_data: dict, resume_data: dict = None, **kwargs) -> dict:
    system_prompt = (
        "You are an expert job fit analyzer. Analyze the job posting against "
        "the candidate's resume/profile and return a structured fit assessment. "
        "Be thorough and objective."
    )
    user_prompt = json.dumps({
        "job": job_data,
        "resume": resume_data or {},
    })

    result = generate(
        task_type='fit_scoring',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=JOB_ANALYSIS_SCHEMA,
        **kwargs,
    )
    return result.get('parsed', result)


def optimize_resume(resume_text: str, job_description: str, **kwargs) -> dict:
    system_prompt = (
        "You are an expert ATS resume optimizer. Analyze the resume against "
        "the job description and provide specific, actionable improvements to "
        "maximize ATS score while maintaining accuracy."
    )
    user_prompt = json.dumps({
        "resume": resume_text,
        "job_description": job_description,
    })

    result = generate(
        task_type='resume_optimization',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=RESUME_OPTIMIZATION_SCHEMA,
        **kwargs,
    )
    return result.get('parsed', result)


def extract_learning_insights(user, organization, applications) -> dict:
    system_prompt = (
        "You are a learning analytics engine. Analyze the user's application history "
        "to identify patterns, what works, what doesn't, and actionable recommendations "
        "for improving their job search strategy."
    )
    user_prompt = json.dumps({
        "total_applications": len(applications),
        "applications": applications[:50],
    })

    result = generate(
        task_type='learning_insight',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        organization_id=str(organization.id),
        user_id=str(user.id),
    )

    parsed = result.get('parsed', result)
    if parsed:
        for pattern_type in ['success_patterns', 'failure_patterns']:
            patterns = parsed.get(pattern_type, [])
            for p in patterns:
                CareerMemory.objects.update_or_create(
                    user=user,
                    organization=organization,
                    memory_type='success_pattern' if 'success' in pattern_type else 'failure_pattern',
                    key=p.get('key', p.get('pattern', 'unknown')),
                    defaults={
                        'value': p,
                        'confidence': p.get('confidence', 0.5),
                        'source': 'learning_engine',
                    },
                )
    return parsed or result
