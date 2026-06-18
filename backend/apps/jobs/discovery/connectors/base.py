import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredJob:
    external_id: str
    title: str
    company_name: str
    location: str = ''
    description: str = ''
    description_html: str = ''
    apply_url: str = ''
    platform: str = ''
    department: str = ''
    seniority: str = ''
    employment_type: str = 'full_time'
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = 'USD'
    remote: Optional[bool] = None
    posted_at: Optional[str] = None
    expires_at: Optional[str] = None
    requirements: list = field(default_factory=list)
    responsibilities: list = field(default_factory=list)
    nice_to_have: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BaseConnector:
    source_name: str = ''
    platform: str = ''

    def discover(
        self,
        titles: list[str] | None = None,
        locations: list[str] | None = None,
        companies: list[str] | None = None,
        max_jobs: int = 50,
    ) -> list[DiscoveredJob]:
        raise NotImplementedError
