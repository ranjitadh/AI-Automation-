from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Recruiter, RecruiterOutreach
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class RecruiterSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Recruiter
        fields = ('id', 'organization', 'company', 'company_name', 'name', 'title', 'email', 'phone', 'linkedin_url', 'source', 'notes', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('organization',)

class RecruiterOutreachSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source='recruiter.name', read_only=True)
    company_name = serializers.CharField(source='recruiter.company.name', read_only=True)

    class Meta:
        model = RecruiterOutreach
        fields = ('id', 'organization', 'recruiter', 'recruiter_name', 'company_name', 'campaign', 'user', 'message_type', 'subject', 'content', 'status', 'sent_at', 'opened_at', 'replied_at', 'open_count', 'click_count', 'created_at', 'updated_at')
        read_only_fields = ('user', 'organization', 'open_count', 'click_count')

class RecruiterViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = Recruiter.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['name', 'title', 'email', 'company__name']
    filterset_fields = ['company', 'source']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'company')

    @action(detail=True, methods=['get'])
    def outreach(self, request, pk=None):
        recruiter = self.get_object()
        msgs = recruiter.outreaches.all()
        return Response(RecruiterOutreachSerializer(msgs, many=True).data)

    @action(detail=True, methods=['post'])
    def outreach_create(self, request, pk=None):
        recruiter = self.get_object()
        s = RecruiterOutreachSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save(recruiter=recruiter, user=request.user, organization=request.org)
        return Response(s.data, status=201)

class RecruiterOutreachViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    queryset = RecruiterOutreach.objects.all()
    serializer_class = RecruiterOutreachSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    search_fields = ['content', 'subject']

    def get_queryset(self):
        return super().get_queryset().select_related('organization', 'recruiter', 'campaign', 'user')
    ordering_fields = ['created_at', 'status']
    filterset_fields = ['status', 'message_type', 'recruiter', 'campaign']
