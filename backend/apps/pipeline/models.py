from django.db import models
from django.conf import settings
from apps.jobs.models import Job
import uuid

class PipelineRun(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='pipeline_runs', db_index=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='pipeline_runs', db_index=True)

    stage = models.CharField(max_length=50, help_text="e.g., research, analysis, generation, submission")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)

    log = models.TextField(blank=True, null=True)

    fit_score = models.IntegerField(null=True, blank=True)
    decision = models.CharField(max_length=20, blank=True)
    bid_score = models.IntegerField(null=True, blank=True)
    throttle_factor = models.FloatField(null=True, blank=True)
    competitiveness_score = models.IntegerField(null=True, blank=True)
    resume_version_id = models.CharField(max_length=100, blank=True)
    application_id = models.CharField(max_length=100, blank=True)
    quality_score = models.IntegerField(null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Run {self.id} for {self.job.title} @ {self.job.company} - {self.status}"
