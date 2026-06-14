from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from .models import PipelineRun
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class PipelineRunSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company', read_only=True)

    class Meta:
        model = PipelineRun
        fields = ('id', 'organization', 'job', 'job_title', 'company_name', 'stage', 'status', 'log', 'started_at', 'completed_at')
        read_only_fields = ('organization', 'started_at', 'completed_at')

class PipelineRunViewSet(OrganizationFilterMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PipelineRun.objects.all()
    serializer_class = PipelineRunSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    filterset_fields = ['status', 'stage']

    def get_queryset(self):
        return super().get_queryset().select_related('job').order_by('-started_at')
