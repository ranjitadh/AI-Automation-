from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin, FileUpload
from pgvector.django import VectorField
import uuid

class Resume(TimeStampedMixin):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes', db_index=True)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='resumes', db_index=True)
    title = models.CharField(max_length=255)
    profile_slug = models.SlugField(max_length=100)
    file = models.ForeignKey(FileUpload, on_delete=models.SET_NULL, null=True, blank=True, related_name='resumes', db_index=True)
    parsed_text = models.TextField(blank=True)
    parsed_html = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    target_role = models.CharField(max_length=255, blank=True)
    target_industries = models.JSONField(default=list, blank=True)
    target_locations = models.JSONField(default=list, blank=True)
    target_salary_min = models.IntegerField(null=True, blank=True)
    target_salary_max = models.IntegerField(null=True, blank=True)
    preferred_remote = models.BooleanField(null=True, blank=True)
    open_to_relocation = models.BooleanField(null=True, blank=True)
    work_authorization = models.CharField(max_length=100, blank=True)
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    seniority_level = models.CharField(max_length=50, blank=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['-is_active', '-created_at']
        unique_together = ['organization', 'profile_slug']

    def __str__(self):
        return f"{self.title} - {self.user.email}"

class ResumeVersion(TimeStampedMixin):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='versions', db_index=True)
    version_number = models.IntegerField()
    file = models.ForeignKey(FileUpload, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    optimized_for_job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    original_text = models.TextField(blank=True)
    optimized_text = models.TextField(blank=True)
    changes_summary = models.JSONField(default=dict, blank=True)
    ats_score = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['resume', 'version_number']

    def __str__(self):
        return f"{self.resume.title} v{self.version_number}"
