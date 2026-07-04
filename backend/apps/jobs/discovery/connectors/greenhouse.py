import logging
from datetime import datetime

import httpx

from .base import BaseConnector, DiscoveredJob

logger = logging.getLogger(__name__)

GREENHOUSE_BOARDS: dict[str, str] = {
    'airbnb': 'airbnb',
    'affirm': 'affirm',
    'asana': 'asana',
    'atlassian': 'atlassian',
    'benchling': 'benchling',
    'betterment': 'betterment',
    'brex': 'brex',
    'canva': 'canva',
    'confluent': 'confluent',
    'coursera': 'coursera',
    'datadog': 'datadog',
    'databricks': 'databricks',
    'deel': 'deel',
    'discord': 'discord',
    'doordash': 'doordash',
    'dropbox': 'dropbox',
    'dbt_labs': 'dbtlabs',
    'duolingo': 'duolingo',
    'etsy': 'etsy',
    'evernote': 'evernote',
    'figma': 'figma',
    'flexport': 'flexport',
    'gametime': 'gametime',
    'ginger': 'ginger',
    'gitlab': 'gitlab',
    'gong': 'gong',
    'grammarly': 'grammarly',
    'gusto': 'gusto',
    'hashicorp': 'hashicorp',
    'hubspot': 'hubspot',
    'instacart': 'instacart',
    'intercom': 'intercom',
    'invision': 'invision',
    'kickstarter': 'kickstarter',
    'looker': 'looker',
    'lyft': 'lyft',
    'medallia': 'medallia',
    'mixpanel': 'mixpanel',
    'mongodb': 'mongodb',
    'monzo': 'monzo',
    'netsuite': 'netsuite',
    'nextdoor': 'nextdoor',
    'notion': 'notion',
    'npm': 'npm',
    'nubank': 'nubank',
    'okta': 'okta',
    'openai': 'openai',
    'opentable': 'opentable',
    'optimizely': 'optimizely',
    'pagerduty': 'pagerduty',
    'palantir': 'palantir',
    'paypal': 'paypal',
    'pinterest': 'pinterest',
    'plaid': 'plaid',
    'postmates': 'postmates',
    'productboard': 'productboard',
    'quora': 'quora',
    'reddit': 'reddit',
    'redfin': 'redfin',
    'revolut': 'revolut',
    'rippling': 'rippling',
    'robinhood': 'robinhood',
    'salesforce': 'salesforce',
    'segment': 'segment',
    'shopify': 'shopify',
    'shortcut': 'shortcut',
    'slack': 'slack',
    'snapchat': 'snap',
    'snyk': 'snyk',
    'sonder': 'sonder',
    'spotify': 'spotify',
    'square': 'square',
    'stripe': 'stripe',
    'superhuman': 'superhuman',
    'tableau': 'tableau',
    'teladoc': 'teladoc',
    'thredd': 'thredd',
    'tinder': 'tinder',
    'twilio': 'twilio',
    'twitter': 'x',
    'typeform': 'typeform',
    'uber': 'uber',
    'upwork': 'upwork',
    'vanta': 'vanta',
    'venmo': 'venmo',
    'vercel': 'vercel',
    'walmart': 'walmart',
    'walmart_labs': 'walmartlabs',
    'warp': 'warp',
    'wayfair': 'wayfair',
    'wework': 'wework',
    'wish': 'wish',
    'workday': 'workday',
    'workiva': 'workiva',
    'yelp': 'yelp',
    'zapier': 'zapier',
    'zendesk': 'zendesk',
    'zoom': 'zoom',
    'zscaler': 'zscaler',
}

SENIORITY_KEYWORDS: dict[str, str] = {
    'intern': 'intern',
    'entry': 'entry',
    'junior': 'entry',
    'mid': 'mid',
    'senior': 'senior',
    'staff': 'lead',
    'lead': 'lead',
    'principal': 'lead',
    'manager': 'manager',
    'director': 'director',
    'head of': 'director',
    'vp': 'executive',
    'vice president': 'executive',
    'chief': 'executive',
    'cfo': 'executive',
    'cto': 'executive',
    'ceo': 'executive',
}


def _infer_seniority(title: str) -> str:
    lower = title.lower()
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in lower:
            return level
    return 'mid'


def _infer_employment_type(title: str, description: str) -> str:
    text = (title + ' ' + description).lower()
    if any(w in text for w in ['intern', 'internship']):
        return 'internship'
    if any(w in text for w in ['contract', 'temporary', 'temp', 'freelance']):
        return 'contract'
    if any(w in text for w in ['part time', 'part-time']):
        return 'part_time'
    return 'full_time'


def _parse_salary(text: str) -> tuple[int | None, int | None, str]:
    import re
    if not text:
        return None, None, 'USD'
    text = text.replace(',', '')
    patterns = [
        r'\$?(\d{2,3})\s*[-–to]+\s*\$?(\d{2,3})\s*(k|K)',
        r'\$?(\d{4,10})\s*[-–to]+\s*\$?(\d{4,10})',
        r'(\d{2,3})\s*k\s*[-–to]+\s*(\d{2,3})\s*k',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 'k' in text.lower() or (a < 1000 and b < 1000):
                a, b = a * 1000, b * 1000
            return min(a, b), max(a, b), 'USD'
    m = re.search(r'\$?(\d{4,10})', text)
    if m:
        v = int(m.group(1))
        return v, v, 'USD'
    return None, None, 'USD'


class GreenhouseConnector(BaseConnector):
    source_name = 'Greenhouse'
    platform = 'greenhouse'

    def __init__(self, boards: dict[str, str] | None = None):
        self.boards = boards or GREENHOUSE_BOARDS
        self._client = httpx.Client(timeout=15)

    def discover(
        self,
        titles: list[str] | None = None,
        locations: list[str] | None = None,
        companies: list[str] | None = None,
        max_jobs: int = 50,
    ) -> list[DiscoveredJob]:
        board_names = list(self.boards.items())
        if companies:
            company_lower = {c.lower() for c in companies}
            board_names = [(k, v) for k, v in board_names if k.lower() in company_lower]

        if not board_names:
            board_names = list(self.boards.items())

        found: list[DiscoveredJob] = []

        for company_slug, board_token in board_names:
            if len(found) >= max_jobs:
                break
            try:
                jobs = self._fetch_board(board_token, company_slug)
                for job_data in jobs:
                    if len(found) >= max_jobs:
                        break
                    job = self._transform(job_data, company_slug)
                    if job and self._matches_criteria(job, titles, locations):
                        found.append(job)
            except Exception as e:
                logger.warning('Greenhouse board %s failed: %s', board_token, e)
                continue

        return found

    def _fetch_board(self, board_token: str, company_slug: str) -> list[dict]:
        url = f'https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs'
        resp = self._client.get(url, params={'content': 'true', 'page': 1, 'per_page': 100})
        resp.raise_for_status()
        data = resp.json()
        return data.get('jobs', [])

    def _transform(self, job_data: dict, company_slug: str) -> DiscoveredJob | None:
        try:
            title = (job_data.get('title') or '').strip()
            if not title:
                return None
            external_id = str(job_data.get('id', ''))
            location = ''
            offices = job_data.get('offices') or []
            if offices:
                loc_parts = []
                for o in offices:
                    city = (o.get('name') or '').strip()
                    state = (o.get('state') or '').strip()
                    country = (o.get('country') or '').strip()
                    part = ', '.join(filter(None, [city, state]))
                    if country:
                        part = f'{part}, {country}' if part else country
                    if part:
                        loc_parts.append(part)
                location = '; '.join(loc_parts)

            desc = (job_data.get('content') or '').strip()
            metadata_obj = job_data.get('metadata') or {}

            apply_url = ''
            if job_data.get('absolute_url'):
                apply_url = job_data['absolute_url']

            posted_at_str = None
            if job_data.get('updated_at'):
                try:
                    dt = datetime.fromisoformat(job_data['updated_at'].replace('Z', '+00:00'))
                    posted_at_str = dt.isoformat()
                except Exception:
                    pass

            salary_text = ''
            for m in metadata_obj:
                if 'salary' in (m.get('name') or '').lower():
                    salary_text = m.get('value') or ''

            salary_min, salary_max, currency = _parse_salary(salary_text or desc)

            seniority = _infer_seniority(title)
            emp_type = _infer_employment_type(title, desc)
            department = ''
            if job_data.get('departments'):
                dept = job_data['departments'][0]
                department = (dept.get('name') or '').strip()

            return DiscoveredJob(
                external_id=f'greenhouse_{external_id}',
                title=title,
                company_name=company_slug.replace('_', ' ').title(),
                location=location,
                description=desc,
                description_html=desc,
                apply_url=apply_url,
                platform='greenhouse',
                department=department,
                seniority=seniority,
                employment_type=emp_type,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                posted_at=posted_at_str,
                metadata={
                    'greenhouse_job_id': external_id,
                    'greenhouse_board': company_slug,
                },
            )
        except Exception as e:
            logger.warning('Failed to transform Greenhouse job: %s', e)
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
