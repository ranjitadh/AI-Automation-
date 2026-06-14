from django.db import models
from apps.common.models import TimeStampedMixin

class JobAnalysis(TimeStampedMixin):
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='analyses', db_index=True)
    resume_profile = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)

    required_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    years_experience_required = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    seniority_level = models.CharField(max_length=50, blank=True)
    education_required = models.CharField(max_length=255, blank=True)
    certifications_required = models.JSONField(default=list, blank=True)
    technologies = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    salary_range = models.JSONField(default=dict, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)

    fit_score = models.IntegerField(default=0)
    ats_score = models.IntegerField(default=0)
    experience_score = models.IntegerField(default=0)
    skill_match_score = models.IntegerField(default=0)
    keyword_score = models.IntegerField(default=0)
    location_score = models.IntegerField(default=0)
    salary_score = models.IntegerField(default=0)
    education_score = models.IntegerField(default=0)
    seniority_score = models.IntegerField(default=0)
    overall_score = models.IntegerField(default=0)

    skill_gaps = models.JSONField(default=list, blank=True)
    experience_gaps = models.JSONField(default=list, blank=True)
    keyword_gaps = models.JSONField(default=list, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    recommendation = models.CharField(max_length=20, choices=(
        ('strong_apply', 'Strong Apply'),
        ('apply', 'Apply'),
        ('consider', 'Consider'),
        ('skip', 'Skip'),
    ), default='consider', db_index=True)

    raw_analysis = models.JSONField(default=dict, blank=True)
    model_used = models.CharField(max_length=100, default='gpt-4o')
    processing_time_ms = models.IntegerField(null=True, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'job analyses'
        unique_together = ['job', 'resume_profile']

    def __str__(self):
        return f"Analysis: {self.job.title} @ {self.job.company.name} ({self.fit_score})"

class ATSAnalysis(TimeStampedMixin):
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='ats_analyses', db_index=True)
    resume = models.ForeignKey('resumes.Resume', on_delete=models.CASCADE, related_name='ats_analyses', db_index=True)
    ats_score = models.IntegerField(default=0)
    keyword_match_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    formatting_score = models.IntegerField(default=0)
    section_score = models.IntegerField(default=0)
    missing_sections = models.JSONField(default=list, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    suggested_improvements = models.JSONField(default=list, blank=True)
    optimized_sections = models.JSONField(default=dict, blank=True)
    raw_analysis = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = 'ats analyses'
        unique_together = ['job', 'resume']

    def __str__(self):
        return f"ATS: {self.resume.title} vs {self.job.title} ({self.ats_score})"
