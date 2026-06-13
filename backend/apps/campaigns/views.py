from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Campaign
from .serializers import CampaignSerializer
from apps.businesses.models import Business
from apps.pipeline.tasks import start_pipeline_for_business

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        campaign = self.get_object()
        
        # Find matching businesses
        businesses = Business.objects.all()
        if campaign.target_category:
            businesses = businesses.filter(category__icontains=campaign.target_category)
            
        count = 0
        for business in businesses:
            start_pipeline_for_business(business.id, campaign_id=campaign.id)
            count += 1
            
        campaign.status = 'active'
        campaign.save()
        
        return Response({'status': 'Campaign started', 'businesses_queued': count})
