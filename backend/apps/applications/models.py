from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class Application(TimeStampedMixin):
    STATUS_CHOICES = (
        ('discovered', 'Discovered'),
        ('analyzed', 'Analyzed'),
        ('approved', 'Approved'),
        ('queued', 'Queued'),
        ('applying', 'Applying'),
        ('submitted', 'Submitted'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('failed', 'Failed'),
    )

    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='applications', db_index=True)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications', db_index=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='applications', db_index=True)
    resume = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications', db_index=True)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications', db_index=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='discovered', db_index=True)
    sub_status = models.CharField(max_length=50, blank=True)

    cover_letter = models.ForeignKey('cover_letters.CoverLetter', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications', db_index=True)
    answers = models.JSONField(default=list, blank=True)
    resume_version = models.ForeignKey('resumes.ResumeVersion', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)

    discovered_at = models.DateTimeField(auto_now_add=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    dispatch_status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ), default='pending', db_index=True)
    dispatch_log = models.TextField(blank=True)
    dispatch_attempts = models.IntegerField(default=0)
    last_dispatched_at = models.DateTimeField(null=True, blank=True)

    screenshot_before = models.ForeignKey('common.FileUpload', on_delete=models.SET_NULL, null=True, blank=True, related_name='screenshots_before', db_index=True)
    screenshot_after = models.ForeignKey('common.FileUpload', on_delete=models.SET_NULL, null=True, blank=True, related_name='screenshots_after', db_index=True)
    confirmation_text = models.TextField(blank=True)
    confirmation_screenshot = models.ForeignKey('common.FileUpload', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmations', db_index=True)
    application_url = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['job', 'applicant']

    def __str__(self):
        return f"{self.job.title} @ {self.job.company.name} - {self.status}"

class ApplicationEvent(TimeStampedMixin):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='events', db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.application.job.title} - {self.event_type}"
