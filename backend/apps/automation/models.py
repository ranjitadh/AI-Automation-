from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class BrowserSession(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='browser_sessions', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='browser_sessions', db_index=True)
    platform = models.CharField(max_length=50, db_index=True)
    session_data = models.JSONField(default=dict, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    proxy = models.TextField(blank=True)
    fingerprint = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=(
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('blocked', 'Blocked'),
        ('error', 'Error'),
    ), default='active', db_index=True)
    error_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ['-last_used_at']
        unique_together = ['organization', 'platform', 'is_active']

    def __str__(self):
        return f"{self.platform} session ({self.status})"

class AutomationRun(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='automation_runs', db_index=True)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='automation_runs', db_index=True)
    application = models.ForeignKey('applications.Application', on_delete=models.SET_NULL, null=True, blank=True, related_name='automation_runs', db_index=True)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='started_runs', db_index=True)

    status = models.CharField(max_length=20, choices=(
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
    ), default='queued', db_index=True)
    stage = models.CharField(max_length=50, blank=True)
    progress = models.IntegerField(default=0)

    headless = models.BooleanField(default=True)
    proxy = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Run {self.id} - {self.status}"

class AutomationLog(TimeStampedMixin):
    automation_run = models.ForeignKey(AutomationRun, on_delete=models.CASCADE, related_name='logs', db_index=True)
    level = models.CharField(max_length=20, choices=(
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ), default='info', db_index=True)
    source = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.level}] {self.message[:100]}"
