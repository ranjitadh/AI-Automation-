import json
import logging
from decimal import Decimal

from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember, IsOrgAdmin

from .models import (
    AIRequest, PromptTemplate, AIBudget, CareerGoal, CareerMemory,
    ApplicationDecision, ApplicationOutcome,
)
from .serializers import (
    AIRequestSerializer, AIRequestDetailSerializer,
    PromptTemplateSerializer, PromptTemplateVersionSerializer,
    AIBudgetSerializer, CareerGoalSerializer, CareerMemorySerializer,
    ApplicationDecisionSerializer, ApplicationOutcomeSerializer,
    AIGenerateSerializer, AgentDecideSerializer,
    OptimizeResumeSerializer, InterviewPrepSerializer, FitScoreSerializer,
    JobMatchAnalyzeSerializer, ResumeAdaptSerializer,
    HumanizedCoverLetterSerializer, ScreeningAnswersSerializer,
    ValidateApplicationSerializer, CalibrateExperienceSerializer,
    RecordOutcomeSerializer, AnalyzePatternsSerializer, WeeklyReportSerializer,
    RecruiterSimulationSerializer, ApplicationQualitySerializer,
    ATSOptimizationSerializer, InterviewMaximizationSerializer,
)
from .gateway import generate as gateway_generate
from .agent import CareerAgent
from .engines import analyze_fit, optimize_resume as engine_optimize_resume
from .interview_agent import prepare_interview
from .budgets import check_budget
from .metrics import get_daily_usage, get_task_type_breakdown, get_provider_breakdown
from .matching_engine import (
    analyze_job_match, calibrate_experience, decide_application,
    load_candidate_profile, build_job_data_from_model,
)
from .resume_adaptation_engine import adapt_resume, create_resume_version
from .humanization_engine import generate_humanized_cover_letter
from .question_answering_engine import generate_screening_answers
from .validation_engine import validate_application, validate_before_submission
from .consistency_engine import verify_application_consistency
from .learning_engine import (
    record_outcome, analyze_patterns, get_weekly_report,
)
from .recruiter_simulation_engine import simulate_recruiter_perspectives
from .application_quality_engine import evaluate_application_quality
from .ats_optimization_engine import evaluate_ats_compatibility, get_ats_optimization_suggestions
from .interview_maximization_engine import (
    compute_interview_maximization, get_optimal_resume_style, get_optimal_salary_range,
)

logger = logging.getLogger(__name__)


class AIRequestViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AIRequest.objects.all()
    serializer_class = AIRequestSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['task_type', 'provider', 'model', 'status', 'error']
    ordering_fields = ['created_at', 'latency_ms', 'cost', 'total_tokens']
    filterset_fields = ['task_type', 'provider', 'model', 'status']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AIRequestDetailSerializer
        return AIRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('organization', 'user')


class AIGenerateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = AIGenerateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        budget = check_budget(str(request.org.id))
        if not budget.get('allowed'):
            return Response(
                {'error': 'AI budget exceeded', 'budget': budget},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        result = gateway_generate(
            task_type=serializer.validated_data['task_type'],
            system_prompt=serializer.validated_data['system_prompt'],
            user_prompt=serializer.validated_data['user_prompt'],
            temperature=serializer.validated_data.get('temperature', 0.3),
            max_tokens=serializer.validated_data.get('max_tokens', 4096),
            model=serializer.validated_data.get('model') or None,
            provider=serializer.validated_data.get('provider') or None,
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )

        if 'error' in result:
            return Response(result, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result)


class AgentDecisionView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = AgentDecideSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agent = CareerAgent(request.user, request.org)
        result = agent.decide(serializer.validated_data['job_data'])
        return Response(result)


class AgentRecommendationsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, *args, **kwargs):
        agent = CareerAgent(request.user, request.org)
        result = agent.get_recommendations()
        return Response(result)


class FitScoreView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = FitScoreSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = analyze_fit(
            serializer.validated_data['job_data'],
            serializer.validated_data.get('resume_data'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class ResumeOptimizeView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = OptimizeResumeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = engine_optimize_resume(
            serializer.validated_data['resume_text'],
            serializer.validated_data['job_description'],
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class InterviewPrepView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = InterviewPrepSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = prepare_interview(
            serializer.validated_data['job_data'],
            serializer.validated_data.get('interview_type', 'technical'),
        )
        return Response(result)


class PromptTemplateViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = PromptTemplate.objects.all()
    serializer_class = PromptTemplateSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin]
    search_fields = ['name', 'task_type', 'system_prompt']
    filterset_fields = ['task_type', 'is_active', 'provider']

    def get_queryset(self):
        return PromptTemplate.objects.filter(
            models.Q(organization=self.request.org) | models.Q(is_system=True)
        )

    def perform_create(self, serializer):
        last_version = PromptTemplate.objects.filter(
            name=serializer.validated_data.get('name')
        ).order_by('-version').first()
        serializer.save(
            version=(last_version.version + 1) if last_version else 1,
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        tmpl = self.get_object()
        PromptTemplate.objects.filter(name=tmpl.name, is_active=True).update(is_active=False)
        tmpl.is_active = True
        tmpl.save(update_fields=['is_active'])
        return Response({'status': 'activated'})

    @action(detail=True)
    def versions(self, request, pk=None):
        tmpl = self.get_object()
        versions = PromptTemplate.objects.filter(name=tmpl.name).order_by('-version')
        serializer = PromptTemplateVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def rollback(self, request):
        name = request.data.get('name')
        version = request.data.get('version')
        if not name or not version:
            return Response({'error': 'name and version required'}, status=400)
        PromptTemplate.objects.filter(name=name, is_active=True).update(is_active=False)
        tmpl = PromptTemplate.objects.filter(name=name, version=version).first()
        if not tmpl:
            return Response({'error': 'version not found'}, status=404)
        new_version = PromptTemplate.objects.filter(name=name).order_by('-version').first()
        new_tmpl = PromptTemplate.objects.create(
            name=tmpl.name,
            version=(new_version.version + 1) if new_version else 1,
            task_type=tmpl.task_type,
            provider=tmpl.provider,
            model=tmpl.model,
            system_prompt=tmpl.system_prompt,
            user_prompt_template=tmpl.user_prompt_template,
            response_schema=tmpl.response_schema,
            temperature=tmpl.temperature,
            max_tokens=tmpl.max_tokens,
            is_active=True,
            is_system=tmpl.is_system,
            metadata=tmpl.metadata,
        )
        serializer = self.get_serializer(new_tmpl)
        return Response(serializer.data)


class AIBudgetViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = AIBudget.objects.all()
    serializer_class = AIBudgetSerializer
    permission_classes = [IsAuthenticated, IsOrgAdmin]

    @action(detail=True)
    def status(self, request, pk=None):
        budget = self.get_object()
        result = check_budget(str(request.org.id))
        return Response(result)


class CareerGoalViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = CareerGoal.objects.all()
    serializer_class = CareerGoalSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['target_titles', 'target_companies', 'target_industries']

    def get_queryset(self):
        return CareerGoal.objects.filter(
            user=self.request.user, organization=self.request.org
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, organization=self.request.org)


class CareerMemoryViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CareerMemory.objects.all()
    serializer_class = CareerMemorySerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    filterset_fields = ['memory_type', 'source']

    def get_queryset(self):
        return CareerMemory.objects.filter(
            user=self.request.user, organization=self.request.org
        ).order_by('-confidence')


class ApplicationDecisionViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationDecision.objects.all()
    serializer_class = ApplicationDecisionSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['decision', 'reasoning', 'auto_reject_reason']
    filterset_fields = ['decision', 'auto_apply', 'overqualification_risk', 'underqualification_risk']

    def get_queryset(self):
        return ApplicationDecision.objects.filter(
            user=self.request.user, organization=self.request.org
        ).select_related('job', 'job__company').order_by('-created_at')


class ApplicationOutcomeViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationOutcome.objects.all()
    serializer_class = ApplicationOutcomeSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    filterset_fields = ['outcome']

    def get_queryset(self):
        return ApplicationOutcome.objects.filter(
            user=self.request.user, organization=self.request.org
        ).select_related('application__job__company').order_by('-created_at')


class JobMatchAnalyzeView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = JobMatchAnalyzeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate = serializer.validated_data.get('candidate_data')
        if not candidate:
            candidate = load_candidate_profile(request.user, request.org)

        result = analyze_job_match(
            serializer.validated_data['job_data'],
            candidate,
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class ResumeAdaptView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = ResumeAdaptSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = adapt_resume(
            serializer.validated_data['resume_data'],
            serializer.validated_data['job_data'],
            serializer.validated_data.get('calibration'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class HumanizedCoverLetterView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = HumanizedCoverLetterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate = serializer.validated_data.get('candidate_data')
        if not candidate:
            candidate = load_candidate_profile(request.user, request.org).get('resume', {})

        result = generate_humanized_cover_letter(
            serializer.validated_data['job_data'],
            candidate,
            style=serializer.validated_data.get('style', 'professional'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class ScreeningAnswersView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = ScreeningAnswersSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate = serializer.validated_data.get('candidate_data')
        if not candidate:
            candidate = load_candidate_profile(request.user, request.org).get('resume', {})

        result = generate_screening_answers(
            serializer.validated_data['questions'],
            candidate,
            serializer.validated_data.get('job_data'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class ValidateApplicationView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = ValidateApplicationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = validate_application(
            serializer.validated_data['resume_exists'],
            serializer.validated_data['cover_letter_exists'],
            serializer.validated_data['fit_score'],
            serializer.validated_data.get('fit_threshold', 70),
            serializer.validated_data.get('answers_generated', False),
            serializer.validated_data.get('candidate_data'),
            serializer.validated_data.get('application_data'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class CalibrateExperienceView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = CalibrateExperienceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = calibrate_experience(
            serializer.validated_data['job_seniority'],
            serializer.validated_data['candidate_seniority'],
            serializer.validated_data['candidate_years'],
            serializer.validated_data.get('job_years_required'),
            serializer.validated_data.get('job_data'),
            serializer.validated_data.get('resume_data'),
            organization_id=str(request.org.id),
            user_id=str(request.user.id),
        )
        return Response(result)


class RecordOutcomeView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = RecordOutcomeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.applications.models import Application
        try:
            app = Application.objects.get(
                id=serializer.validated_data['application_id'],
                organization=request.org,
            )
        except Application.DoesNotExist:
            return Response({'error': 'Application not found'}, status=404)

        outcome = record_outcome(
            app,
            serializer.validated_data['outcome'],
            serializer.validated_data.get('rejection_reason'),
            serializer.validated_data.get('feedback'),
            serializer.validated_data.get('interview_rounds'),
            serializer.validated_data.get('offer_amount'),
        )
        ser = ApplicationOutcomeSerializer(outcome)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class AnalyzePatternsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = AnalyzePatternsSerializer

    def get(self, request, *args, **kwargs):
        result = analyze_patterns(request.user, request.org)
        return Response(result)


class WeeklyReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = WeeklyReportSerializer

    def get(self, request, *args, **kwargs):
        result = get_weekly_report(request.user, request.org)
        return Response(result)


class AIAnalyticsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request, *args, **kwargs):
        days = int(request.query_params.get('days', 30))
        daily = get_daily_usage(str(request.org.id), days)
        by_task = get_task_type_breakdown(str(request.org.id), days)
        by_provider = get_provider_breakdown(str(request.org.id), days)

        totals = AIRequest.objects.filter(
            organization=request.org,
            created_at__gte=timezone.now() - timedelta(days=days),
        ).aggregate(
            total_requests=Count('id'),
            total_cost=Sum('cost'),
            total_tokens=Sum('total_tokens'),
            avg_latency=Avg('latency_ms'),
        )

        budget_status = check_budget(str(request.org.id))

        return Response({
            'totals': totals,
            'daily': list(daily),
            'by_task': list(by_task),
            'by_provider': list(by_provider),
            'budget': budget_status,
            'period_days': days,
        })


class RecruiterSimulationView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = RecruiterSimulationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = simulate_recruiter_perspectives(
            resume_data=serializer.validated_data['resume_data'],
            cover_letter_text=serializer.validated_data['cover_letter_text'],
            screening_answers=serializer.validated_data.get('screening_answers', []),
            profile_data=serializer.validated_data.get('profile_data', {}),
            job_data=serializer.validated_data['job_data'],
        )
        return Response(result)


class ApplicationQualityView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = ApplicationQualitySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = evaluate_application_quality(
            resume_data=serializer.validated_data['resume_data'],
            cover_letter_text=serializer.validated_data['cover_letter_text'],
            screening_answers=serializer.validated_data.get('screening_answers', []),
            profile_data=serializer.validated_data.get('profile_data', {}),
            job_data=serializer.validated_data['job_data'],
        )
        return Response(result)


class ATSOptimizationView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = ATSOptimizationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resume_data = serializer.validated_data['resume_data']
        job_platform = serializer.validated_data.get('job_platform', '')

        if job_platform:
            suggestions = get_ats_optimization_suggestions(resume_data, job_platform)
            return Response({
                "platform_specific": True,
                "platform": job_platform,
                "suggestions": suggestions,
            })

        result = evaluate_ats_compatibility(resume_data)
        return Response(result)


class InterviewMaximizationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = InterviewMaximizationSerializer

    def get(self, request, *args, **kwargs):
        maximization = compute_interview_maximization(request.user, request.org)
        resume_style = get_optimal_resume_style(request.user, request.org)
        salary_range = get_optimal_salary_range(request.user, request.org)

        return Response({
            **maximization,
            "optimal_resume_style": resume_style,
            "optimal_salary_range": salary_range,
        })


import django.db.models as models


class ConsistencyCheckView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def create(self, request, *args, **kwargs):
        resume_data = request.data.get('resume_data', {})
        cover_letter_text = request.data.get('cover_letter_text', '')
        screening_answers = request.data.get('screening_answers', [])
        profile_data = request.data.get('profile_data', {})
        job_data = request.data.get('job_data')

        result = verify_application_consistency(
            resume_data=resume_data,
            cover_letter_text=cover_letter_text,
            screening_answers=screening_answers,
            profile_data=profile_data,
            job_data=job_data,
        )
        return Response(result)
