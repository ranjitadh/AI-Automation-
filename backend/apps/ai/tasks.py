import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
    queue='ai',
)
def task_ai_generate(task_type, system_prompt, user_prompt, **kwargs):
    from .gateway import generate
    return generate(
        task_type=task_type,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        **kwargs,
    )


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
    queue='ai',
)
def task_analyze_job(job_id, organization_id=None, user_id=None):
    from apps.jobs.models import Job
    from apps.resumes.models import Resume
    from .engines import analyze_fit

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None

    job_data = {
        'title': job.title,
        'description': job.description,
        'requirements': job.requirements or [],
        'company': job.company.name if job.company else None,
        'location': job.location,
        'salary_min': job.salary_min,
        'salary_max': job.salary_max,
        'seniority': job.seniority,
    }

    resume = Resume.objects.filter(is_active=True).first()
    resume_data = None
    if resume:
        resume_data = {
            'title': resume.title,
            'summary': resume.summary,
            'skills': resume.skills or [],
            'experience': resume.experience or [],
            'years_of_experience': resume.years_of_experience,
            'seniority_level': resume.seniority_level,
        }

    result = analyze_fit(
        job_data, resume_data,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='ai',
)
def task_generate_learning_insights(organization_id, user_id):
    from apps.applications.models import Application
    from .engines import extract_learning_insights
    from django.contrib.auth import get_user_model
    from apps.accounts.models import Organization

    user = get_user_model().objects.get(id=user_id)
    org = Organization.objects.get(id=organization_id)
    apps = Application.objects.filter(organization=org).values(
        'id', 'status', 'created_at', 'job__title', 'job__company__name'
    )[:100]

    return extract_learning_insights(user, org, list(apps))
