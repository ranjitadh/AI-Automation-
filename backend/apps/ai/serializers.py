from rest_framework import serializers
from .models import (
    AIRequest, PromptTemplate, AIBudget, CareerGoal, CareerMemory,
    ApplicationDecision, ApplicationOutcome,
)


class AIRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequest
        fields = (
            'id', 'organization', 'user', 'task_type', 'provider', 'model',
            'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost',
            'latency_ms', 'status', 'error', 'prompt_id', 'cache_hit',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class AIRequestDetailSerializer(AIRequestSerializer):
    class Meta(AIRequestSerializer.Meta):
        fields = AIRequestSerializer.Meta.fields + ('metadata',)


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = (
            'id', 'name', 'version', 'task_type', 'provider', 'model',
            'system_prompt', 'user_prompt_template', 'response_schema',
            'temperature', 'max_tokens', 'is_active', 'is_system',
            'metadata', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'version', 'created_at', 'updated_at')


class PromptTemplateVersionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    version = serializers.IntegerField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class AIBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIBudget
        fields = (
            'id', 'organization', 'daily_limit_cents', 'weekly_limit_cents',
            'monthly_limit_cents', 'soft_limit_pct', 'is_active',
            'alert_email', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CareerGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerGoal
        fields = (
            'id', 'user', 'organization',
            'target_titles', 'target_salary_min', 'target_salary_max',
            'target_companies', 'target_industries', 'target_locations',
            'remote_preference', 'open_to_relocation',
            'visa_sponsorship_needed', 'work_authorization',
            'seniority_level', 'employment_type',
            'min_skills', 'preferred_skills', 'excluded_skills',
            'excluded_companies', 'excluded_titles',
            'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CareerMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerMemory
        fields = (
            'id', 'user', 'organization', 'memory_type', 'key', 'value',
            'confidence', 'source', 'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ApplicationDecisionSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationDecision
        fields = (
            'id', 'user', 'organization', 'job', 'job_title', 'company_name',
            'decision', 'fit_score', 'skill_match_score', 'experience_match_score',
            'seniority_match_score', 'industry_match_score', 'salary_match_score',
            'location_match_score', 'overqualification_risk', 'underqualification_risk',
            'auto_reject_reason', 'reasoning', 'confidence', 'threshold_used',
            'auto_apply', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def get_job_title(self, obj):
        return obj.job.title if obj.job_id else ''

    def get_company_name(self, obj):
        return obj.job.company.name if obj.job and obj.job.company else ''


class ApplicationOutcomeSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationOutcome
        fields = (
            'id', 'application', 'user', 'organization',
            'job_title', 'company_name',
            'outcome', 'response_time_days', 'interview_rounds', 'offer_amount',
            'rejection_reason', 'feedback', 'notes',
            'resume_version_used', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_job_title(self, obj):
        return obj.application.job.title if obj.application_id else ''

    def get_company_name(self, obj):
        return obj.application.job.company.name if obj.application and obj.application.job and obj.application.job.company else ''


class AIGenerateSerializer(serializers.Serializer):
    task_type = serializers.ChoiceField(choices=[
        'job_parsing', 'resume_parsing', 'skill_extraction',
        'company_analysis', 'classification', 'tagging',
        'bulk_processing', 'ats_analysis', 'resume_optimization',
        'career_agent_reasoning', 'interview_preparation',
        'cover_letter', 'question_answering', 'fit_scoring',
        'decision_making', 'learning_insight',
    ])
    system_prompt = serializers.CharField()
    user_prompt = serializers.CharField()
    temperature = serializers.FloatField(default=0.3, min_value=0.0, max_value=2.0)
    max_tokens = serializers.IntegerField(default=4096, min_value=1, max_value=32768)
    model = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.CharField(required=False, allow_blank=True)


class AgentDecideSerializer(serializers.Serializer):
    job_data = serializers.JSONField()


class OptimizeResumeSerializer(serializers.Serializer):
    resume_text = serializers.CharField()
    job_description = serializers.CharField()


class InterviewPrepSerializer(serializers.Serializer):
    job_data = serializers.JSONField()
    interview_type = serializers.ChoiceField(
        choices=['technical', 'behavioral', 'phone', 'onsite', 'system_design', 'general'],
        default='technical',
    )


class FitScoreSerializer(serializers.Serializer):
    job_data = serializers.JSONField()
    resume_data = serializers.JSONField(required=False, allow_null=True)


class JobMatchAnalyzeSerializer(serializers.Serializer):
    job_data = serializers.JSONField()
    candidate_data = serializers.JSONField(required=False, allow_null=True)


class ResumeAdaptSerializer(serializers.Serializer):
    resume_data = serializers.JSONField()
    job_data = serializers.JSONField()
    calibration = serializers.JSONField(required=False, allow_null=True)


class HumanizedCoverLetterSerializer(serializers.Serializer):
    job_data = serializers.JSONField()
    candidate_data = serializers.JSONField(required=False, allow_null=True)
    style = serializers.ChoiceField(
        choices=['professional', 'direct', 'storytelling', 'enthusiastic'],
        default='professional',
    )


class ScreeningAnswersSerializer(serializers.Serializer):
    questions = serializers.ListField(child=serializers.CharField())
    candidate_data = serializers.JSONField(required=False, allow_null=True)
    job_data = serializers.JSONField(required=False, allow_null=True)


class ValidateApplicationSerializer(serializers.Serializer):
    resume_exists = serializers.BooleanField()
    cover_letter_exists = serializers.BooleanField()
    fit_score = serializers.IntegerField(min_value=0, max_value=100)
    fit_threshold = serializers.IntegerField(default=70, min_value=0, max_value=100)
    answers_generated = serializers.BooleanField(default=False)
    candidate_data = serializers.JSONField(required=False, allow_null=True)
    application_data = serializers.JSONField(required=False, allow_null=True)


class CalibrateExperienceSerializer(serializers.Serializer):
    job_seniority = serializers.CharField()
    candidate_seniority = serializers.CharField()
    candidate_years = serializers.FloatField()
    job_years_required = serializers.FloatField(required=False, allow_null=True)
    job_data = serializers.JSONField(required=False, allow_null=True)
    resume_data = serializers.JSONField(required=False, allow_null=True)


class RecordOutcomeSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    outcome = serializers.ChoiceField(choices=[
        'no_response', 'rejected', 'screen', 'interview', 'offer', 'accepted', 'withdrawn',
    ])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    feedback = serializers.CharField(required=False, allow_blank=True)
    interview_rounds = serializers.IntegerField(required=False, allow_null=True)
    offer_amount = serializers.IntegerField(required=False, allow_null=True)


class AnalyzePatternsSerializer(serializers.Serializer):
    pass


class WeeklyReportSerializer(serializers.Serializer):
    pass
