from django.db import models
from apps.businesses.models import Business
import uuid

class PipelineRun(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='pipeline_runs')
    
    stage = models.CharField(max_length=50, help_text="e.g., research, analysis, generation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    log = models.TextField(blank=True, null=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Run {self.id} for {self.business.name} - {self.status}"
