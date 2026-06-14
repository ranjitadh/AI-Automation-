from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class CoverLetter(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='cover_letters', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cover_letters', db_index=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True, related_name='cover_letters', db_index=True)
    resume = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, related_name='cover_letters', db_index=True)
    version = models.IntegerField(default=1)

    style = models.CharField(max_length=20, choices=(
        ('short', 'Short'),
        ('medium', 'Medium'),
        ('long', 'Long'),
        ('custom', 'Custom'),
    ), default='medium', db_index=True)
    tone = models.CharField(max_length=50, default='professional')
    length = models.IntegerField(default=0)

    subject = models.CharField(max_length=500, blank=True)
    salutation = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    closing = models.TextField(blank=True)
    content = models.TextField(blank=True)

    model_used = models.CharField(max_length=100, default='gpt-4o')
    prompt_template = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    is_approved = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cover Letter for {self.job.title if self.job else 'N/A'} ({self.style})"
