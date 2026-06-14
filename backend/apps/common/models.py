from django.db import models
from django.conf import settings
from .fields import EncryptedTextField
import uuid

class TimeStampedMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class FileUpload(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='file_uploads', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='file_uploads', db_index=True)
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.BigIntegerField()
    storage_path = models.TextField()
    storage_bucket = models.CharField(max_length=255, blank=True)
    storage_provider = models.CharField(max_length=50, default='local')
    checksum = models.CharField(max_length=64, blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=100, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class OrganizationSettings(models.Model):
    organization = models.OneToOneField('accounts.Organization', on_delete=models.CASCADE, related_name='settings')
    default_timezone = models.CharField(max_length=50, default='UTC')
    default_locale = models.CharField(max_length=10, default='en')
    default_min_fit_score = models.IntegerField(default=70)
    max_applications_per_day = models.IntegerField(default=20)
    default_cover_letter_style = models.CharField(max_length=20, default='medium')
    require_approval = models.BooleanField(default=True)
    application_window_start = models.TimeField(null=True, blank=True)
    application_window_end = models.TimeField(null=True, blank=True)
    default_resume = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    auto_optimize_resume = models.BooleanField(default=False)
    stealth_mode = models.BooleanField(default=True)
    proxy_enabled = models.BooleanField(default=False)
    proxy_config = models.JSONField(default=dict, blank=True)
    browser_fingerprint_rotation = models.BooleanField(default=True)
    human_like_delays = models.BooleanField(default=True)
    retry_on_failure = models.BooleanField(default=True)
    max_retries = models.IntegerField(default=3)
    captcha_handling = models.CharField(max_length=50, default='manual')
    email_notifications = models.BooleanField(default=True)
    slack_webhook_url = models.TextField(blank=True)
    discord_webhook_url = models.TextField(blank=True)
    linkedin_username = models.TextField(blank=True)
    linkedin_password = EncryptedTextField(blank=True)
    indeed_username = models.TextField(blank=True)
    indeed_password = EncryptedTextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'organization settings'

    def __str__(self):
        return f"Settings for {self.organization.name}"
