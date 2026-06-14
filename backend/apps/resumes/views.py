from rest_framework import viewsets, serializers, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Resume, ResumeVersion
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ('id', 'organization', 'user', 'file', 'title', 'profile_slug', 'parsed_text', 'parsed_html', 'skills', 'experience', 'education', 'certifications', 'projects', 'summary', 'target_role', 'target_industries', 'target_locations', 'target_salary_min', 'target_salary_max', 'preferred_remote', 'open_to_relocation', 'work_authorization', 'years_of_experience', 'seniority_level', 'embedding', 'is_active', 'version', 'created_at', 'updated_at')
        read_only_fields = ('user', 'organization', 'embedding', 'version')

class ResumeVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeVersion
        fields = ('id', 'resume', 'version_number', 'file', 'optimized_for_job', 'original_text', 'optimized_text', 'changes_summary', 'ats_score', 'is_active', 'created_at', 'updated_at')

class ResumeViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['title', 'summary', 'target_role']

    def get_queryset(self):
        return super().get_queryset().select_related('user', 'organization', 'file').prefetch_related('versions')
    filterset_fields = ['is_active', 'seniority_level', 'work_authorization']

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        Resume.objects.filter(organization=request.org, is_active=True).update(is_active=False)
        r = self.get_object()
        r.is_active = True
        r.save(update_fields=['is_active'])
        return Response({'status': 'active', 'id': str(r.id)})

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        r = self.get_object()
        versions = r.versions.all()
        return Response(ResumeVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=['post'])
    def embed(self, request, pk=None):
        r = self.get_object()
        from tasks.embedding_tasks import generate_resume_embedding
        generate_resume_embedding.delay(str(r.id))
        return Response({'status': 'embedding queued'})
