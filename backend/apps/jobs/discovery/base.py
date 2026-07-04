import logging
from typing import Optional

from django.utils import timezone

from apps.jobs.models import Company, Job, JobSource
from .connectors.base import DiscoveredJob
from .connectors.greenhouse import GreenhouseConnector
from .connectors.lever import LeverConnector
from .connectors.ashby import AshbyConnector

logger = logging.getLogger(__name__)

CONNECTORS: list[type] = [
    GreenhouseConnector,
    LeverConnector,
    AshbyConnector,
]


def discover_jobs(
    titles: Optional[list[str]] = None,
    locations: Optional[list[str]] = None,
    companies: Optional[list[str]] = None,
    campaign=None,
    max_jobs: int = 100,
) -> list[Job]:
    logger.info(
        'Discovering jobs titles=%s locations=%s companies=%s',
        titles, locations, companies,
    )

    all_discovered: list[DiscoveredJob] = []

    for connector_cls in CONNECTORS:
        try:
            connector = connector_cls()
            jobs = connector.discover(
                titles=titles,
                locations=locations,
                companies=companies,
                max_jobs=max_jobs,
            )
            logger.info(
                '%s connector found %d jobs',
                connector.source_name, len(jobs),
            )
            all_discovered.extend(jobs)
        except Exception as e:
            logger.error('%s connector failed: %s', connector_cls.__name__, e)

    source, _ = JobSource.objects.get_or_create(
        name='Public ATS APIs',
        defaults={
            'connector_type': 'api',
            'config': {
                'connectors': [c.__name__ for c in CONNECTORS],
            },
            'is_enabled': True,
        },
    )

    created_jobs: list[Job] = []
    for discovered in all_discovered:
        try:
            job = _upsert_job(discovered, source)
            if job:
                created_jobs.append(job)
        except Exception as e:
            logger.warning('Failed to upsert job %s: %s', discovered.title, e)

    source.last_synced_at = timezone.now()
    source.save(update_fields=['last_synced_at'])

    logger.info('Discovery complete: %d new/updated jobs', len(created_jobs))
    return created_jobs


def _upsert_job(discovered: DiscoveredJob, source: JobSource) -> Optional[Job]:
    company, _ = Company.objects.get_or_create(
        name__iexact=discovered.company_name,
        defaults={
            'name': discovered.company_name,
        },
    )

    job, created = Job.objects.update_or_create(
        source=source,
        external_id=discovered.external_id,
        defaults={
            'company': company,
            'title': discovered.title,
            'location': discovered.location,
            'description': discovered.description,
            'description_html': discovered.description_html,
            'apply_url': discovered.apply_url,
            'platform': discovered.platform,
            'department': discovered.department,
            'seniority': discovered.seniority,
            'employment_type': discovered.employment_type,
            'salary_min': discovered.salary_min,
            'salary_max': discovered.salary_max,
            'salary_currency': discovered.salary_currency,
            'remote': discovered.remote,
            'posted_at': discovered.posted_at,
            'scraped_at': timezone.now(),
            'is_active': True,
            'metadata': discovered.metadata,
        },
    )

    if created:
        logger.debug('Created job: %s @ %s', job.title, company.name)
    else:
        logger.debug('Updated job: %s @ %s', job.title, company.name)

    return job
