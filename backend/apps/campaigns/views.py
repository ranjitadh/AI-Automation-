from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Campaign
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember, IsOrgAdmin
from apps.jobs.models import Job

class CampaignSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = ('id', 'organization', 'created_by', 'created_by_name', 'name', 'description', 'status', 'target_titles', 'target_locations', 'target_companies', 'target_industries', 'target_salary_min', 'target_salary_max', 'target_remote', 'target_seniority', 'target_skills', 'exclude_titles', 'exclude_companies', 'keywords', 'resume_profile', 'auto_apply', 'require_approval', 'max_applications_per_day', 'min_fit_score', 'application_window_start', 'application_window_end', 'schedule_frequency', 'schedule_start', 'schedule_end', 'last_run_at', 'next_run_at', 'jobs_found', 'jobs_analyzed', 'applications_submitted', 'interviews_booked', 'created_at', 'updated_at', 'application_count')
        read_only_fields = ('created_by', 'organization', 'last_run_at', 'next_run_at',
                           'jobs_found', 'jobs_analyzed', 'applications_submitted', 'interviews_booked')

    def get_application_count(self, obj):
        return obj.applications.count()

class CampaignViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'status']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'created_by', 'resume_profile').prefetch_related('applications')
    filterset_fields = ['status', 'auto_apply', 'schedule_frequency']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, organization=self.request.org)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'active'
        campaign.save(update_fields=['status'])
        from tasks.discovery_tasks import run_campaign_discovery
        run_campaign_discovery.delay(str(campaign.id))
        return Response({'status': 'campaign started'})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
        return Response({'status': 'campaign paused'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = 'active'
        campaign.save(update_fields=['status'])
        return Response({'status': 'campaign resumed'})

    @action(detail=True)
    def stats(self, request, pk=None):
        campaign = self.get_object()
        return Response({
            'jobs_found': campaign.jobs_found,
            'jobs_analyzed': campaign.jobs_analyzed,
            'applications_submitted': campaign.applications_submitted,
            'interviews_booked': campaign.interviews_booked,
        })
