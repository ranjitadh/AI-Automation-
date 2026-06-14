from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin
from pgvector.django import VectorField
import uuid

class JobSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='job_sources', db_index=True)
    name = models.CharField(max_length=100)
    connector_type = models.CharField(max_length=50, choices=(
        ('api', 'API'), ('scrape', 'Scrape'), ('webhook', 'Webhook'),
    ))
    config = models.JSONField(default=dict, blank=True)
    is_enabled = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['organization', 'name']

    def __str__(self):
        return self.name

class Company(TimeStampedMixin):
    name = models.CharField(max_length=255, db_index=True)
    domain = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=255, blank=True, db_index=True)
    size = models.CharField(max_length=50, blank=True)
    headquarters = models.CharField(max_length=255, blank=True)
    locations = models.JSONField(default=list, blank=True)
    logo_url = models.TextField(blank=True)
    careers_page_url = models.TextField(blank=True)
    ats_provider = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name

class Job(TimeStampedMixin):
    SENIORITY_CHOICES = (
        ('intern', 'Internship'),
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead / Staff'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('executive', 'Executive'),
    )
    EMPLOYMENT_CHOICES = (
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary'),
    )

    external_id = models.CharField(max_length=255, blank=True)
    source = models.ForeignKey(JobSource, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs', db_index=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, blank=True, db_index=True)
    remote = models.BooleanField(null=True, blank=True)
    hybrid = models.BooleanField(null=True, blank=True)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='USD')
    salary_period = models.CharField(max_length=20, default='yearly')
    description = models.TextField(blank=True)
    description_html = models.TextField(blank=True)
    requirements = models.JSONField(default=list, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    nice_to_have = models.JSONField(default=list, blank=True)
    apply_url = models.TextField(blank=True)
    direct_apply_url = models.TextField(blank=True)
    platform = models.CharField(max_length=50, blank=True, db_index=True)
    department = models.CharField(max_length=255, blank=True, db_index=True)
    function = models.CharField(max_length=255, blank=True, db_index=True)
    seniority = models.CharField(max_length=20, choices=SENIORITY_CHOICES, blank=True, db_index=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='full_time', db_index=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scraped_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_remote_eligible = models.BooleanField(null=True, blank=True)
    visa_sponsorship = models.BooleanField(null=True, blank=True)
    application_count = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        ordering = ['-posted_at', '-created_at']
        unique_together = ['source', 'external_id']

    def __str__(self):
        return f"{self.title} @ {self.company.name}"
