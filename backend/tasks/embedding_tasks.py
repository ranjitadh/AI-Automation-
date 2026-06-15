import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
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
    queue='embedding',
)
def generate_resume_embedding(resume_id):
    from apps.analysis.services import get_embedding
    try:
        resume = Resume.objects.get(id=resume_id)
    except ObjectDoesNotExist:
        logger.error(f"Resume {resume_id} not found")
        return None
    text = f"{resume.summary or ''} {' '.join(s.get('description', '') for s in (resume.experience or []))}"
    embedding = get_embedding(text)
    if embedding:
        resume.embedding = embedding
        resume.save(update_fields=['embedding'])
        logger.info(f"Generated embedding for resume {resume.title}")
    return resume_id


