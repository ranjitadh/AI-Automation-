from rest_framework import viewsets
from .models import PipelineRun
from .serializers import PipelineRunSerializer

class PipelineRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PipelineRun.objects.all().order_by('-started_at')
    serializer_class = PipelineRunSerializer
    filterset_fields = ['status', 'stage']
