import logging
from datetime import datetime

import httpx

from .base import BaseConnector, DiscoveredJob

logger = logging.getLogger(__name__)

LEVER_DOMAINS: dict[str, str] = {
    'affirm': 'affirm',
    'airbnb': 'airbnb',
    'amazon': 'amazon',
    'amplitude': 'amplitude',
    'asana': 'asana',
    'atlassian': 'atlassian',
    'benchling': 'benchling',
    'box': 'box',
    'brex': 'brex',
    'canva': 'canva',
    'checkr': 'checkr',
    'clari': 'clari',
    'confluent': 'confluent',
    'coursera': 'coursera',
    'databricks': 'databricks',
    'deel': 'deel',
    'doordash': 'doordash',
    'dropbox': 'dropbox',
    'dbt_labs': 'dbtlabs',
    'duolingo': 'duolingo',
    'elastic': 'elastic',
    'etsy': 'etsy',
    'eventbrite': 'eventbrite',
    'eway': 'eway',
    'figma': 'figma',
    'flexport': 'flexport',
    'ginkgo': 'ginkgobioworks',
    'gitlab': 'gitlab',
    'glossier': 'glossier',
    'gong': 'gong',
    'grammarly': 'grammarly',
    'gusto': 'gusto',
    'hashicorp': 'hashicorp',
    'hubspot': 'hubspot',
    'hulu': 'hulu',
    'instacart': 'instacart',
    'intercom': 'intercom',
    'lattice': 'lattice',
    'linear': 'linear',
    'loom': 'loom',
    'lyft': 'lyft',
    'maven': 'maven',
    'mixpanel': 'mixpanel',
    'mongodb': 'mongodb',
    'nervos': 'nervos',
    'netflix': 'netflix',
    'nextdoor': 'nextdoor',
    'notion': 'notion',
    'okta': 'okta',
    'openai': 'openai',
    'opentable': 'opentable',
    'pagerduty': 'pagerduty',
    'palantir': 'palantir',
    'paypal': 'paypal',
    'pinterest': 'pinterest',
    'plaid': 'plaid',
    'postmates': 'postmates',
    'quora': 'quora',
    'reddit': 'reddit',
    'redfin': 'redfin',
    'revolut': 'revolut',
    'rippling': 'rippling',
    'robinhood': 'robinhood',
    'segment': 'segment',
    'shopify': 'shopify',
    'slack': 'slack',
    'snapchat': 'snap',
    'snyk': 'snyk',
    'spotify': 'spotify',
    'square': 'squareup',
    'stripe': 'stripe',
    'superhuman': 'superhuman',
    'teladoc': 'teladoc',
    'tinder': 'tinder',
    'twilio': 'twilio',
    'uber': 'uber',
    'upwork': 'upwork',
    'venmo': 'venmo',
    'vercel': 'vercel',
    'vimeo': 'vimeo',
    'walmart': 'walmart',
    'warp': 'warp',
    'wayfair': 'wayfair',
    'weWork': 'wework',
    'wish': 'wish',
    'workiva': 'workiva',
    'yelp': 'yelp',
    'zapier': 'zapier',
    'zendesk': 'zendesk',
    'zillow': 'zillow',
    'zoom': 'zoom',
}


class LeverConnector(BaseConnector):
    source_name = 'Lever'
    platform = 'lever'

    def __init__(self, domains: dict[str, str] | None = None):
        self.domains = domains or LEVER_DOMAINS
        self._client = httpx.Client(timeout=15)

    def discover(
        self,
        titles: list[str] | None = None,
        locations: list[str] | None = None,
        companies: list[str] | None = None,
        max_jobs: int = 50,
    ) -> list[DiscoveredJob]:
        domain_items = list(self.domains.items())
        if companies:
            company_lower = {c.lower() for c in companies}
            domain_items = [(k, v) for k, v in domain_items if k.lower() in company_lower]

        if not domain_items:
            domain_items = list(self.domains.items())

        found: list[DiscoveredJob] = []

        for company_slug, domain in domain_items:
            if len(found) >= max_jobs:
                break
            try:
                jobs = self._fetch_postings(domain, company_slug)
                for job_data in jobs:
                    if len(found) >= max_jobs:
                        break
                    job = self._transform(job_data, company_slug)
                    if job and self._matches_criteria(job, titles, locations):
                        found.append(job)
            except Exception as e:
                logger.warning('Lever domain %s failed: %s', domain, e)
                continue

        return found

    def _fetch_postings(self, domain: str, company_slug: str) -> list[dict]:
        url = f'https://api.lever.co/v0/postings/{domain}?mode=json'
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    def _transform(self, job_data: dict, company_slug: str) -> DiscoveredJob | None:
        try:
            title = (job_data.get('text') or '').strip()
            if not title:
                title = (job_data.get('title') or '').strip()
            if not title:
                return None

            external_id = str(job_data.get('id', ''))
            location = (job_data.get('categories', {}).get('location') or '').strip()
            if not location:
                location = (job_data.get('office') or '').strip()
            desc = (job_data.get('descriptionPlain') or job_data.get('description') or '').strip()
            desc_html = (job_data.get('description') or '').strip()
            apply_url = job_data.get('applyUrl') or job_data.get('urls', {}).get('apply', '') or ''
            department = (job_data.get('categories', {}).get('team') or '').strip()

            salary_text = (job_data.get('salary') or job_data.get('categories', {}).get('salary') or '')
            salary_min, salary_max, currency = None, None, 'USD'
            if salary_text:
                import re
                m = re.search(r'\$?(\d{2,6})\s*[-–to]+\s*\$?(\d{2,6})', salary_text.replace(',', ''))
                if m:
                    a, b = int(m.group(1)), int(m.group(2))
                    salary_min, salary_max = min(a, b), max(a, b)

            posted_at_str = None
            if job_data.get('createdAt'):
                try:
                    ts = job_data['createdAt'] / 1000
                    dt = datetime.fromtimestamp(ts)
                    posted_at_str = dt.isoformat()
                except Exception:
                    pass

            from .greenhouse import _infer_seniority, _infer_employment_type

            seniority = _infer_seniority(title)
            emp_type = _infer_employment_type(title, desc)

            remote = None
            loc_lower = location.lower()
            if any(w in loc_lower for w in ['remote', 'anywhere']):
                remote = True
            elif loc_lower and 'remote' not in loc_lower:
                remote = False

            return DiscoveredJob(
                external_id=f'lever_{external_id}',
                title=title,
                company_name=company_slug.replace('_', ' ').title(),
                location=location,
                description=desc,
                description_html=desc_html,
                apply_url=apply_url,
                platform='lever',
                department=department,
                seniority=seniority,
                employment_type=emp_type,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
                remote=remote,
                posted_at=posted_at_str,
                metadata={
                    'lever_job_id': external_id,
                    'lever_domain': company_slug,
                },
            )
        except Exception as e:
            logger.warning('Failed to transform Lever job: %s', e)
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
