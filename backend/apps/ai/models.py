import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class AIRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('fallback', 'Fallback'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='ai_requests', null=True, blank=True, db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='ai_requests', null=True, blank=True, db_index=True,
    )
    task_type = models.CharField(max_length=100, db_index=True)
    provider = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('0'))
    latency_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    error = models.TextField(blank=True, null=True)
    prompt_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    cache_hit = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'task_type']),
            models.Index(fields=['organization', 'created_at']),
        ]

    def __str__(self):
        return f"{self.task_type} [{self.provider}/{self.model}] {self.status}"


class PromptTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    version = models.PositiveIntegerField(default=1)
    task_type = models.CharField(max_length=100, db_index=True)
    provider = models.CharField(max_length=50, default='gemini')
    model = models.CharField(max_length=100, blank=True, null=True)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(blank=True, null=True)
    response_schema = models.JSONField(default=dict, blank=True,
        help_text="JSON Schema for structured output validation")
    temperature = models.FloatField(default=0.3, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)])
    max_tokens = models.IntegerField(default=4096)
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_prompt_templates'
        ordering = ['-version']
        unique_together = [('name', 'version')]
        indexes = [
            models.Index(fields=['task_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} v{self.version} ({self.task_type})"


class AIBudget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='ai_budgets', db_index=True,
    )
    daily_limit_cents = models.IntegerField(default=5000)
    weekly_limit_cents = models.IntegerField(default=35000)
    monthly_limit_cents = models.IntegerField(default=150000)
    soft_limit_pct = models.FloatField(default=80.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    is_active = models.BooleanField(default=True)
    alert_email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_budgets'
        verbose_name_plural = 'AI budgets'

    def __str__(self):
        return f"Budget for {self.organization.name}"


class CareerGoal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='career_goals', db_index=True,
    )
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='career_goals', db_index=True,
    )

    target_titles = models.JSONField(default=list, blank=True)
    target_salary_min = models.IntegerField(null=True, blank=True)
    target_salary_max = models.IntegerField(null=True, blank=True)
    target_companies = models.JSONField(default=list, blank=True)
    target_industries = models.JSONField(default=list, blank=True)
    target_locations = models.JSONField(default=list, blank=True)
    remote_preference = models.CharField(max_length=20, choices=[
        ('remote', 'Remote Only'),
        ('hybrid', 'Hybrid'),
        ('onsite', 'On-site'),
        ('any', 'Any'),
    ], default='any')
    open_to_relocation = models.BooleanField(default=False)
    visa_sponsorship_needed = models.BooleanField(default=False)
    work_authorization = models.CharField(max_length=50, blank=True, null=True)

    seniority_level = models.CharField(max_length=30, blank=True, null=True)
    employment_type = models.CharField(max_length=30, default='full_time')

    min_skills = models.JSONField(default=list, blank=True)
    preferred_skills = models.JSONField(default=list, blank=True)
    excluded_skills = models.JSONField(default=list, blank=True)
    excluded_companies = models.JSONField(default=list, blank=True)
    excluded_titles = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'career_goals'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} goals ({', '.join(self.target_titles[:3])})"


class CareerMemory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='career_memories', db_index=True,
    )
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='career_memories', db_index=True,
    )
    memory_type = models.CharField(max_length=50, choices=[
        ('success_pattern', 'Success Pattern'),
        ('failure_pattern', 'Failure Pattern'),
        ('insight', 'Insight'),
        ('preference', 'Preference'),
        ('feedback', 'Feedback'),
        ('observation', 'Observation'),
    ], db_index=True)
    key = models.CharField(max_length=200, db_index=True)
    value = models.JSONField(default=dict)
    confidence = models.FloatField(default=0.5, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    source = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'career_memories'
        ordering = ['-confidence']
        unique_together = [('user', 'memory_type', 'key')]
        indexes = [
            models.Index(fields=['user', 'memory_type']),
        ]

    def __str__(self):
        return f"{self.memory_type}: {self.key} ({self.confidence})"


class ApplicationDecision(models.Model):
    DECISION_CHOICES = [
        ('apply', 'Apply'),
        ('reject', 'Reject'),
        ('review', 'Review'),
        ('queue', 'Queue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='application_decisions', db_index=True,
    )
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='application_decisions', db_index=True,
    )
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='decisions', db_index=True)

    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, db_index=True)
    fit_score = models.IntegerField(default=0)
    skill_match_score = models.IntegerField(default=0)
    experience_match_score = models.IntegerField(default=0)
    seniority_match_score = models.IntegerField(default=0)
    industry_match_score = models.IntegerField(default=0)
    salary_match_score = models.IntegerField(default=0)
    location_match_score = models.IntegerField(default=0)
    overqualification_risk = models.CharField(max_length=20, default='none')
    underqualification_risk = models.CharField(max_length=20, default='none')
    auto_reject_reason = models.TextField(blank=True)
    reasoning = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)

    threshold_used = models.IntegerField(default=70)
    auto_apply = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'application_decisions'
        ordering = ['-created_at']
        unique_together = [('user', 'job')]

    def __str__(self):
        return f"{self.decision}: {self.job.title} ({self.fit_score})"


class ApplicationOutcome(models.Model):
    OUTCOME_CHOICES = [
        ('no_response', 'No Response'),
        ('rejected', 'Rejected'),
        ('screen', 'Screen'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('accepted', 'Accepted'),
        ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'applications.Application', on_delete=models.CASCADE,
        related_name='outcomes', db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='application_outcomes', db_index=True,
    )
    organization = models.ForeignKey(
        'accounts.Organization', on_delete=models.CASCADE,
        related_name='application_outcomes', db_index=True,
    )

    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='no_response', db_index=True)
    response_time_days = models.IntegerField(null=True, blank=True)
    interview_rounds = models.IntegerField(null=True, blank=True)
    offer_amount = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    resume_version_used = models.ForeignKey(
        'resumes.ResumeVersion', on_delete=models.SET_NULL, null=True, blank=True,
    )
    cover_letter_version = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'application_outcomes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application.job.title} - {self.outcome}"
