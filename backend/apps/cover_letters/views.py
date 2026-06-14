from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CoverLetter
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class CoverLetterSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True, allow_null=True)

    class Meta:
        model = CoverLetter
        fields = ('id', 'organization', 'user', 'job', 'job_title', 'company_name', 'resume', 'version', 'style', 'tone', 'length', 'subject', 'salutation', 'body', 'closing', 'content', 'model_used', 'prompt_template', 'raw_response', 'is_approved', 'is_used', 'created_at', 'updated_at')
        read_only_fields = ('user', 'organization', 'model_used', 'raw_response', 'version')

class CoverLetterViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = CoverLetter.objects.all()
    serializer_class = CoverLetterSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['job__title']
    ordering_fields = ['created_at', 'style']
    filterset_fields = ['style', 'tone', 'job', 'is_approved', 'is_used']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'user', 'job', 'resume')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, organization=self.request.org)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        job_id = request.data.get('job')
        resume_id = request.data.get('resume')
        style = request.data.get('style', 'medium')
        if not job_id:
            return Response({'error': 'job required'}, status=400)
        from tasks.cover_letter_tasks import generate_cover_letter_task
        task = generate_cover_letter_task.delay(job_id, resume_id, style, str(request.user.id), str(request.org.id))
        return Response({'status': 'generating', 'task_id': task.id})
