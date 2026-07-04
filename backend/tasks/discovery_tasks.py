import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.campaigns.models import Campaign
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
    queue='discovery',
)
def run_campaign_discovery(campaign_id):
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except ObjectDoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return None
    logger.info(f"Running discovery for campaign {campaign.name}")

    titles = campaign.target_titles or []
    locations = campaign.target_locations or []
    companies = campaign.target_companies or []

    from apps.jobs.discovery.base import discover_jobs
    jobs = discover_jobs(titles, locations, companies, campaign)

    campaign.jobs_found = Job.objects.filter(
        title__in=titles if titles else Job.objects.values('title')
    ).count()
    campaign.last_run_at = timezone.now()
    campaign.save(update_fields=['jobs_found', 'last_run_at'])

    for job in jobs:
        from tasks.analysis_tasks import analyze_job_task
        analyze_job_task.delay(str(job.id), str(campaign.id))

    logger.info(f"Discovery complete for {campaign.name}: {len(jobs)} jobs found")
    return len(jobs)


