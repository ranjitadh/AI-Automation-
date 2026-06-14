from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class Notification(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='notifications', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', db_index=True)
    type = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=50, choices=(
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('discord', 'Discord'),
        ('webhook', 'Webhook'),
    ), default='in_app', db_index=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['organization', 'type', '-created_at']),
        ]

    def __str__(self):
        return self.title

class Webhook(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='webhooks', db_index=True)
    url = models.URLField(max_length=500)
    secret = models.TextField(blank=True)
    events = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Webhook {self.url}"
