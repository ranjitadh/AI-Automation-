import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.campaigns.models import Campaign
from apps.jobs.models import Job, Company, JobSource

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
def discover_single_job(url, platform='generic'):
    from apps.jobs.discovery.generic import scrape_job_from_url
    job_data = scrape_job_from_url(url, platform)
    if job_data:
        company, _ = Company.objects.get_or_create(
            name=job_data.get('company', 'Unknown'),
            defaults={'domain': job_data.get('domain', '')}
        )
        source, _ = JobSource.objects.get_or_create(
            name=platform,
            defaults={'connector_type': 'scrape'}
        )
        job, created = Job.objects.get_or_create(
            external_id=job_data.get('external_id', url),
            defaults={
                'company': company,
                'source': source,
                'title': job_data.get('title', 'Unknown'),
                'location': job_data.get('location', ''),
                'description': job_data.get('description', ''),
                'apply_url': job_data.get('apply_url', url),
                'platform': platform,
                'scraped_at': timezone.now(),
            }
        )
        return str(job.id)
    return None
