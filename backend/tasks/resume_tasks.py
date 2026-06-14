import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from apps.resumes.models import Resume, ResumeVersion
from apps.jobs.models import Job

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
    queue='resume',
)
def parse_resume_file(resume_id):
    try:
        resume = Resume.objects.get(id=resume_id)
    except ObjectDoesNotExist:
        logger.error(f"Resume {resume_id} not found")
        return None
    logger.info(f"Parsing resume {resume.title}")
    from apps.resumes.parsers import parse_resume
    result = parse_resume(resume.file.storage_path if resume.file else None)
    if result:
        resume.parsed_text = result.get('text', '')
        resume.parsed_html = result.get('html', '')
        resume.skills = result.get('skills', [])
        resume.experience = result.get('experience', [])
        resume.education = result.get('education', [])
        resume.save(update_fields=['parsed_text', 'parsed_html', 'skills', 'experience', 'education'])
    return resume_id

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='resume',
)
def optimize_resume_for_job(resume_id, job_id):
    from apps.analysis.services import optimize_resume
    try:
        resume = Resume.objects.get(id=resume_id)
    except ObjectDoesNotExist:
        logger.error(f"Resume {resume_id} not found")
        return None
    job = None
    if job_id:
        try:
            job = Job.objects.get(id=job_id)
        except ObjectDoesNotExist:
            logger.error(f"Job {job_id} not found")
    result = optimize_resume(resume, job)
    if result:
        version = resume.version + 1
        ResumeVersion.objects.create(
            resume=resume,
            version_number=version,
            optimized_text=result.get('optimized_text', ''),
            changes_summary=result.get('changes', {}),
            ats_score=result.get('ats_score', 0),
            optimized_for_job=job,
            is_active=True,
        )
        resume.version = version
        resume.save(update_fields=['version'])
    return resume_id
