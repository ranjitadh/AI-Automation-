from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import BrowserSession, AutomationRun, AutomationLog
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class BrowserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrowserSession
        fields = ('id', 'organization', 'user', 'platform', 'session_data', 'user_agent', 'proxy', 'fingerprint', 'is_active', 'last_used_at', 'status', 'error_count', 'last_error', 'created_at', 'updated_at')
        read_only_fields = ('user', 'organization', 'last_used_at', 'error_count', 'last_error')

class AutomationRunSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source='campaign.name', read_only=True, allow_null=True)
    started_by_name = serializers.CharField(source='started_by.full_name', read_only=True, allow_null=True)

    class Meta:
        model = AutomationRun
        fields = ('id', 'organization', 'campaign', 'campaign_name', 'application', 'started_by', 'started_by_name', 'status', 'stage', 'progress', 'headless', 'proxy', 'retry_count', 'max_retries', 'started_at', 'completed_at', 'duration_ms', 'created_at', 'updated_at')
        read_only_fields = ('organization', 'started_at', 'completed_at', 'duration_ms')

class AutomationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationLog
        fields = ('id', 'automation_run', 'level', 'source', 'message', 'metadata', 'created_at')

class BrowserSessionViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = BrowserSession.objects.all()
    serializer_class = BrowserSessionSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['platform']
    ordering_fields = ['created_at', 'status']
    filterset_fields = ['platform', 'status', 'is_active']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, organization=self.request.org)

class AutomationRunViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AutomationRun.objects.all()
    serializer_class = AutomationRunSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    filterset_fields = ['status', 'stage', 'campaign', 'application']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'campaign', 'application', 'started_by')
    ordering_fields = ['-created_at']

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        run = self.get_object()
        run.status = 'canceled'
        run.save(update_fields=['status'])
        return Response({'status': 'canceled'})

    @action(detail=True)
    def logs(self, request, pk=None):
        run = self.get_object()
        logs = run.logs.all()
        page = self.paginate_queryset(logs)
        return self.get_paginated_response(AutomationLogSerializer(page, many=True).data)

class AutomationLogViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AutomationLog.objects.all()
    serializer_class = AutomationLogSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['message', 'source']
    ordering_fields = ['created_at', 'level']
    filterset_fields = ['automation_run', 'level', 'source']

    def get_queryset(self):
        return super().get_queryset().select_related('automation_run')
