from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Application, ApplicationEvent
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True, allow_null=True)
    resume_title = serializers.CharField(source='resume.title', read_only=True, allow_null=True)

    class Meta:
        model = Application
        fields = ('id', 'organization', 'campaign', 'campaign_name', 'job', 'job_title', 'company_name', 'resume', 'resume_title', 'applicant', 'status', 'sub_status', 'cover_letter', 'answers', 'resume_version', 'discovered_at', 'analyzed_at', 'approved_at', 'submitted_at', 'responded_at', 'dispatch_status', 'dispatch_log', 'dispatch_attempts', 'last_dispatched_at', 'screenshot_before', 'screenshot_after', 'confirmation_text', 'confirmation_screenshot', 'application_url', 'created_at', 'updated_at')
        read_only_fields = ('organization', 'applicant', 'discovered_at', 'dispatch_attempts')

class ApplicationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationEvent
        fields = ('id', 'application', 'event_type', 'metadata', 'created_by', 'created_at')

class ApplicationViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['job__title', 'job__company__name']
    ordering_fields = ['created_at', 'status', 'dispatch_status']
    filterset_fields = ['status', 'dispatch_status', 'campaign', 'job']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'campaign', 'job', 'resume', 'applicant', 'cover_letter')

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user, organization=self.request.org)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        app = self.get_object()
        app.dispatch_status = 'pending'
        app.save(update_fields=['dispatch_status'])
        from tasks.automation_tasks import run_application_automation
        run_application_automation.delay(str(app.id))
        return Response({'status': 'auto-apply queued'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        membership = request.user.memberships.filter(organization=request.org).first()
        if not membership or membership.role not in ('owner', 'admin'):
            return Response({'error': 'Only admins can approve applications'}, status=403)
        app = self.get_object()
        app.status = 'approved'
        app.approved_at = timezone.now()
        app.save(update_fields=['status', 'approved_at'])
        ApplicationEvent.objects.create(application=app, event_type='approved', created_by=request.user)
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        membership = request.user.memberships.filter(organization=request.org).first()
        if not membership or membership.role not in ('owner', 'admin'):
            return Response({'error': 'Only admins can reject applications'}, status=403)
        app = self.get_object()
        app.status = 'rejected'
        app.sub_status = request.data.get('reason', '')
        app.save(update_fields=['status', 'sub_status'])
        ApplicationEvent.objects.create(application=app, event_type='rejected', created_by=request.user)
        return Response({'status': 'rejected'})

    @action(detail=False)
    def approval_queue(self, request):
        qs = self.get_queryset().filter(organization=request.org, status='analyzed')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(ApplicationSerializer(page, many=True).data)

    @action(detail=True)
    def events(self, request, pk=None):
        app = self.get_object()
        events = app.events.all()
        return Response(ApplicationEventSerializer(events, many=True).data)
