from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Interview, Offer
from apps.common.mixins import OrganizationFilterMixin
from apps.common.permissions import IsOrgMember

class InterviewSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='application.job.title', read_only=True)
    company_name = serializers.CharField(source='application.job.company.name', read_only=True)

    class Meta:
        model = Interview
        fields = ('id', 'organization', 'application', 'job_title', 'company_name', 'interview_type', 'round', 'status', 'scheduled_at', 'duration_minutes', 'completed_at', 'interviewers', 'feedback', 'rating', 'notes', 'follow_up_action', 'follow_up_date', 'created_at', 'updated_at')
        read_only_fields = ('organization',)

class OfferSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='application.job.title', read_only=True)
    company_name = serializers.CharField(source='application.job.company.name', read_only=True)

    class Meta:
        model = Offer
        fields = ('id', 'organization', 'application', 'job_title', 'company_name', 'status', 'base_salary', 'bonus', 'equity', 'signing_bonus', 'benefits', 'start_date', 'relocation_package', 'offer_date', 'deadline', 'response_date', 'counter_offer_amount', 'counter_offer_details', 'negotiation_notes', 'created_at', 'updated_at')
        read_only_fields = ('organization',)

class InterviewViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    queryset = Interview.objects.select_related('application', 'organization', 'application__job').all()
    filterset_fields = ['status', 'interview_type', 'application']
    ordering_fields = ['scheduled_at']

class OfferViewSet(OrganizationFilterMixin, viewsets.ModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated, IsOrgMember]
    queryset = Offer.objects.select_related('application', 'organization', 'application__job').all()
    filterset_fields = ['status', 'application']
