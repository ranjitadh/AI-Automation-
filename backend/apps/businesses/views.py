from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Business
from .serializers import BusinessSerializer
from apps.pipeline.tasks import start_pipeline_for_business

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all().order_by('-created_at')
    serializer_class = BusinessSerializer
    filterset_fields = ['category', 'has_website']

    @action(detail=True, methods=['post'])
    def run_pipeline(self, request, pk=None):
        business = self.get_object()
        run_id = start_pipeline_for_business(business.id)
        return Response({'status': 'Pipeline started', 'run_id': str(run_id)})
