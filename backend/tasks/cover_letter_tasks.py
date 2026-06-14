import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from apps.cover_letters.models import CoverLetter
from apps.cover_letters.generators import generate_cover_letter as gen_cl
from apps.jobs.models import Job
from apps.resumes.models import Resume

logger = logging.getLogger(__name__)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='cover_letter',
)
def generate_cover_letter_task(job_id, resume_id=None, style='medium', user_id=None, org_id=None):
    try:
        job = Job.objects.get(id=job_id)
    except ObjectDoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None
    resume = None
    if resume_id:
        try:
            resume = Resume.objects.get(id=resume_id)
        except ObjectDoesNotExist:
            logger.error(f"Resume {resume_id} not found")
    result = gen_cl(job, resume, style)
    if result:
        cl = CoverLetter.objects.create(
            organization_id=org_id,
            user_id=user_id,
            job=job,
            resume=resume,
            style=style,
            tone='professional',
            length=len(result.get('body', '').split()),
            subject=result.get('subject', ''),
            salutation=result.get('salutation', 'Dear Hiring Manager,'),
            body=result.get('body', ''),
            closing=result.get('closing', 'Sincerely,'),
            content=result.get('body', ''),
            model_used='gpt-4o',
            raw_response=result,
            version=1,
        )
        return str(cl.id)
    return None
