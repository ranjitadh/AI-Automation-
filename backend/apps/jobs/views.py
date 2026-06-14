from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Job, Company, JobSource
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name', 'domain', 'description', 'industry', 'size', 'headquarters', 'locations', 'logo_url', 'careers_page_url', 'ats_provider', 'is_verified', 'metadata', 'created_at', 'updated_at')

class JobSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSource
        fields = ('id', 'organization', 'name', 'connector_type', 'config', 'is_enabled', 'last_synced_at', 'created_at')

class JobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_logo = serializers.CharField(source='company.logo_url', read_only=True)

    class Meta:
        model = Job
        fields = ('id', 'external_id', 'source', 'company', 'company_name', 'company_logo', 'title', 'location', 'remote', 'hybrid', 'salary_min', 'salary_max', 'salary_currency', 'salary_period', 'description', 'description_html', 'requirements', 'responsibilities', 'nice_to_have', 'apply_url', 'direct_apply_url', 'platform', 'department', 'function', 'seniority', 'employment_type', 'posted_at', 'expires_at', 'scraped_at', 'is_active', 'is_remote_eligible', 'visa_sponsorship', 'application_count', 'metadata', 'embedding', 'created_at', 'updated_at')
        read_only_fields = ('application_count', 'embedding', 'scraped_at')

class JobViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]
    queryset = Job.objects.select_related('company', 'source').all()
    search_fields = ['title', 'company__name', 'location', 'description']
    filterset_fields = ['platform', 'seniority', 'employment_type', 'remote', 'is_active', 'source']
    ordering_fields = ['posted_at', 'salary_min', 'salary_max', 'created_at']

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        job = self.get_object()
        from tasks.analysis_tasks import analyze_job_task
        analyze_job_task.delay(str(job.id))
        return Response({'status': 'analysis queued'})

    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        job = self.get_object()
        analyses = job.analyses.all()
        if analyses:
            from apps.analysis.views import JobAnalysisSerializer
            return Response(JobAnalysisSerializer(analyses.first()).data)
        return Response({'error': 'No analysis found'}, status=404)

class CompanyViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    queryset = Company.objects.all()
    search_fields = ['name', 'domain', 'industry']
    filterset_fields = ['industry', 'is_verified', 'ats_provider']
