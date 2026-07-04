from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import JobAnalysis, ATSAnalysis
from apps.common.mixins import OrganizationFilterMixin

class JobAnalysisSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)

    class Meta:
        model = JobAnalysis
        fields = ('id', 'job', 'job_title', 'company_name', 'resume_profile', 'required_skills', 'preferred_skills', 'years_experience_required', 'seniority_level', 'education_required', 'certifications_required', 'technologies', 'keywords', 'salary_range', 'responsibilities', 'benefits', 'fit_score', 'ats_score', 'experience_score', 'skill_match_score', 'keyword_score', 'location_score', 'salary_score', 'education_score', 'seniority_score', 'overall_score', 'skill_gaps', 'experience_gaps', 'keyword_gaps', 'strengths', 'weaknesses', 'recommendations', 'recommendation', 'raw_analysis', 'model_used', 'processing_time_ms', 'analyzed_at', 'created_at', 'updated_at')

class ATSAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATSAnalysis
        fields = ('id', 'job', 'resume', 'ats_score', 'keyword_match_rate', 'formatting_score', 'section_score', 'missing_sections', 'missing_keywords', 'suggested_improvements', 'optimized_sections', 'raw_analysis', 'created_at', 'updated_at')

class JobAnalysisViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = JobAnalysis.objects.all()
    serializer_class = JobAnalysisSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['job__title']
    ordering_fields = ['created_at', 'fit_score']
    filterset_fields = ['job', 'resume_profile', 'recommendation']

    def get_queryset(self):
        return super().get_queryset().select_related('job', 'resume_profile')

    @action(detail=False, methods=['post'])
    def fit(self, request):
        job_id = request.data.get('job')
        resume_id = request.data.get('resume')
        if not job_id:
            return Response({'error': 'job required'}, status=400)
        from tasks.analysis_tasks import analyze_job_fit_task
        analyze_job_fit_task.delay(job_id, resume_id)
        return Response({'status': 'fit analysis queued'})

    @action(detail=False, methods=['post'])
    def extract_skills(self, request):
        from apps.analysis.analyzers.skill_extractor import extract_skills
        text = request.data.get('text', '')
        skills = extract_skills(text)
        return Response({'skills': skills})

class ATSAnalysisViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ATSAnalysis.objects.all()
    serializer_class = ATSAnalysisSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['job__title']
    ordering_fields = ['created_at', 'overall_score']
    filterset_fields = ['job', 'resume']

    def get_queryset(self):
        return super().get_queryset().select_related('job', 'resume')
