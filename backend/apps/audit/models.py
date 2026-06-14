from django.db import models
from apps.common.models import TimeStampedMixin

class AuditLog(models.Model):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs', db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.CharField(max_length=255, null=True, blank=True)
    resource_description = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['organization', 'resource_type', 'resource_id']),
            models.Index(fields=['organization', 'user', '-timestamp']),
            models.Index(fields=['organization', 'action', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.action} {self.resource_type} by {self.user_id}"
