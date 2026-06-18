import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Discover jobs from public ATS APIs (Greenhouse, Lever, Ashby)'

    def add_arguments(self, parser):
        parser.add_argument('--titles', nargs='*', help='Filter by job titles')
        parser.add_argument('--locations', nargs='*', help='Filter by locations')
        parser.add_argument('--companies', nargs='*', help='Filter by company names')
        parser.add_argument('--max', type=int, default=100, help='Max jobs to fetch')

    def handle(self, *args, **options):
        from apps.jobs.discovery import discover_jobs

        jobs = discover_jobs(
            titles=options['titles'],
            locations=options['locations'],
            companies=options['companies'],
            max_jobs=options['max'],
        )

        self.stdout.write(self.style.SUCCESS(f'Discovered {len(jobs)} jobs'))
        for job in jobs:
            self.stdout.write(f'  - {job.title} @ {job.company.name}')
