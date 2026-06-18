import logging
from datetime import datetime

import httpx

from .base import BaseConnector, DiscoveredJob

logger = logging.getLogger(__name__)

ASHBY_BOARDS: dict[str, str] = {
    'airbnb': 'airbnb',
    'canva': 'canva',
    'confluent': 'confluent',
    'datadog': 'datadog',
    'deel': 'deel',
    'discord': 'discord',
    'doordash': 'doordash',
    'dropbox': 'dropbox',
    'figma': 'figma',
    'gem': 'gem',
    'gusto': 'gusto',
    'hubspot': 'hubspot',
    'intercom': 'intercom',
    'linear': 'linear',
    'lucid': 'lucid',
    'mongodb': 'mongodb',
    'notion': 'notion',
    'okta': 'okta',
    'rippling': 'rippling',
    'segment': 'segment',
    'sentry': 'sentry',
    'snyk': 'snyk',
    'stripe': 'stripe',
    'superhuman': 'superhuman',
    'twilio': 'twilio',
    'vercel': 'vercel',
    'workiva': 'workiva',
    'zapier': 'zapier',
}


class AshbyConnector(BaseConnector):
    source_name = 'Ashby'
    platform = 'ashby'

    def __init__(self, boards: dict[str, str] | None = None):
        self.boards = boards or ASHBY_BOARDS
        self._client = httpx.Client(timeout=15)

    def discover(
        self,
        titles: list[str] | None = None,
        locations: list[str] | None = None,
        companies: list[str] | None = None,
        max_jobs: int = 50,
    ) -> list[DiscoveredJob]:
        board_items = list(self.boards.items())
        if companies:
            company_lower = {c.lower() for c in companies}
            board_items = [(k, v) for k, v in board_items if k.lower() in company_lower]

        if not board_items:
            board_items = list(self.boards.items())

        found: list[DiscoveredJob] = []

        for company_slug, board_token in board_items:
            if len(found) >= max_jobs:
                break
            try:
                jobs = self._fetch_postings(board_token, company_slug)
                for job_data in jobs:
                    if len(found) >= max_jobs:
                        break
                    job = self._transform(job_data, company_slug)
                    if job and self._matches_criteria(job, titles, locations):
                        found.append(job)
            except Exception as e:
                logger.warning('Ashby board %s failed: %s', board_token, e)
                continue

        return found

    def _fetch_postings(self, board_token: str, company_slug: str) -> list[dict]:
        url = f'https://api.ashbyhq.com/posting-api/job-board/{board_token}'
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get('jobs', [])

    def _transform(self, job_data: dict, company_slug: str) -> DiscoveredJob | None:
        try:
            title = (job_data.get('title') or '').strip()
            if not title:
                return None

            external_id = str(job_data.get('id', ''))
            location = (job_data.get('location') or '').strip()
            job_id = job_data.get('jobId', job_data.get('id', ''))
            apply_url = f'https://jobs.ashbyhq.com/{company_slug}/{job_id}'
            department = (job_data.get('department') or job_data.get('team') or '').strip()
            desc = (job_data.get('descriptionHtml') or job_data.get('description') or '').strip()
            desc_plain = (job_data.get('descriptionPlain') or '').strip()

            salary_text = ''
            if job_data.get('salaryRange'):
                sr = job_data['salaryRange']
                min_sr = sr.get('min')
                max_sr = sr.get('max')
                salary_min = int(min_sr) if min_sr else None
                salary_max = int(max_sr) if max_sr else None
                currency = sr.get('currency', 'USD')
            else:
                salary_min = salary_max = None
                currency = 'USD'

            posted_at_str = None
            if job_data.get('publishedAt'):
                try:
                    dt = datetime.fromisoformat(job_data['publishedAt'].replace('Z', '+00:00'))
                    posted_at_str = dt.isoformat()
                except Exception:
                    pass

            from .greenhouse import _infer_seniority, _infer_employment_type

            seniority = _infer_seniority(title)
            emp_type = _infer_employment_type(title, desc or desc_plain)

            return DiscoveredJob(
                external_id=f'ashby_{external_id}',
                title=title,
                company_name=company_slug.replace('_', ' ').title(),
                location=location,
                description=desc_plain or desc,
                description_html=desc or '',
                apply_url=apply_url,
                platform='ashby',
                department=department,
                seniority=seniority,
                employment_type=emp_type,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                posted_at=posted_at_str,
                metadata={
                    'ashby_job_id': external_id,
                    'ashby_board': company_slug,
                },
            )
        except Exception as e:
            logger.warning('Failed to transform Ashby job: %s', e)
            return None

    @staticmethod
    def _matches_criteria(
        job: DiscoveredJob,
        titles: list[str] | None,
        locations: list[str] | None,
    ) -> bool:
        if titles:
            title_lower = job.title.lower()
            if not any(t.lower() in title_lower for t in titles):
                return False
        if locations:
            loc_lower = job.location.lower()
            if not any(l.lower() in loc_lower for l in locations):
                return False
        return True
