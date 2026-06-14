from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class Campaign(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='campaigns', db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns', db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ), default='draft', db_index=True)

    target_titles = models.JSONField(default=list, blank=True)
    target_locations = models.JSONField(default=list, blank=True)
    target_companies = models.JSONField(default=list, blank=True)
    target_industries = models.JSONField(default=list, blank=True)
    target_salary_min = models.IntegerField(null=True, blank=True)
    target_salary_max = models.IntegerField(null=True, blank=True)
    target_remote = models.BooleanField(null=True, blank=True)
    target_seniority = models.JSONField(default=list, blank=True)
    target_skills = models.JSONField(default=list, blank=True)
    exclude_titles = models.JSONField(default=list, blank=True)
    exclude_companies = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)

    resume_profile = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns', db_index=True)
    auto_apply = models.BooleanField(default=False)
    require_approval = models.BooleanField(default=True)
    max_applications_per_day = models.IntegerField(default=20)
    min_fit_score = models.IntegerField(default=70)
    application_window_start = models.TimeField(null=True, blank=True)
    application_window_end = models.TimeField(null=True, blank=True)

    schedule_frequency = models.CharField(max_length=20, choices=(
        ('one_time', 'One Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('continuous', 'Continuous'),
    ), default='one_time')
    schedule_start = models.DateTimeField(null=True, blank=True)
    schedule_end = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    jobs_found = models.IntegerField(default=0)
    jobs_analyzed = models.IntegerField(default=0)
    applications_submitted = models.IntegerField(default=0)
    interviews_booked = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['organization', 'name']

    def __str__(self):
        return f"{self.name} ({self.status})"
