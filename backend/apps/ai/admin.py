from django.contrib import admin
from .models import (
    AIRequest, PromptTemplate, AIBudget, CareerGoal, CareerMemory,
    ApplicationDecision, ApplicationOutcome,
)


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ('task_type', 'provider', 'model', 'status', 'cost', 'latency_ms', 'created_at')
    list_filter = ('task_type', 'provider', 'status', 'created_at')
    search_fields = ('task_type', 'provider', 'model', 'error')
    date_hierarchy = 'created_at'


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'task_type', 'provider', 'is_active')
    list_filter = ('task_type', 'provider', 'is_active')
    search_fields = ('name', 'task_type')


@admin.register(AIBudget)
class AIBudgetAdmin(admin.ModelAdmin):
    list_display = ('organization', 'daily_limit_cents', 'weekly_limit_cents', 'monthly_limit_cents', 'is_active')
    list_filter = ('is_active',)


@admin.register(CareerGoal)
class CareerGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'remote_preference', 'seniority_level', 'is_active', 'created_at')
    list_filter = ('remote_preference', 'is_active')


@admin.register(CareerMemory)
class CareerMemoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'memory_type', 'key', 'confidence', 'source', 'created_at')
    list_filter = ('memory_type', 'source')


@admin.register(ApplicationDecision)
class ApplicationDecisionAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'decision', 'fit_score', 'auto_apply', 'created_at')
    list_filter = ('decision', 'auto_apply', 'created_at')
    search_fields = ('job__title', 'reasoning')


@admin.register(ApplicationOutcome)
class ApplicationOutcomeAdmin(admin.ModelAdmin):
    list_display = ('user', 'outcome', 'response_time_days', 'interview_rounds', 'offer_amount', 'created_at')
    list_filter = ('outcome', 'created_at')
