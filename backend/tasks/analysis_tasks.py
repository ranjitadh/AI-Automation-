import logging
import time
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.jobs.models import Job
from apps.analysis.models import JobAnalysis
from apps.analysis.services import analyze_job_fit
from apps.resumes.models import Resume
from apps.campaigns.models import Campaign
from apps.applications.models import Application
from apps.notifications.services import create_notification

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
    queue='analysis',
)
def analyze_job_task(job_id, campaign_id=None):
    try:
        job = Job.objects.get(id=job_id)
    except ObjectDoesNotExist:
        logger.error(f"Job {job_id} not found")
        return None
    logger.info(f"Analyzing job {job.title} @ {job.company.name}")

    resume = None
    if campaign_id:
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except ObjectDoesNotExist:
            logger.error(f"Campaign {campaign_id} not found")
            campaign = None
        if campaign and campaign.resume_profile:
            resume = campaign.resume_profile
        elif campaign:
            resume = Resume.objects.filter(organization=campaign.organization, is_active=True).first()
    else:
        resume = Resume.objects.filter(is_active=True).first()

    start = time.time()
    analysis = analyze_job_fit(job, resume)
    elapsed = int((time.time() - start) * 1000)

    job_analysis, _ = JobAnalysis.objects.update_or_create(
        job=job, resume_profile=resume,
        defaults={
            **analysis,
            'processing_time_ms': elapsed,
            'model_used': 'gpt-4o',
            'analyzed_at': timezone.now(),
        }
    )

    job.fit_score = analysis.get('fit_score', 0)
    job.save(update_fields=['fit_score'])

    Application.objects.get_or_create(
        job=job,
        applicant__isnull=False,
        defaults={
            'organization': job.company if hasattr(job.company, 'organization') else None,
            'status': 'analyzed',
            'analyzed_at': timezone.now(),
        }
    )

    create_notification(
        org_id=getattr(job.company, 'organization_id', None),
        user_id=None,
        type='job_analyzed',
        title=f"Job analyzed: {job.title}",
        body=f"Fit score: {job_analysis.fit_score}/100",
    )

    return str(job_analysis.id)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='analysis',
)
def analyze_job_fit_task(job_id, resume_id=None):
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
    analysis = analyze_job_fit(job, resume)
    return analysis


