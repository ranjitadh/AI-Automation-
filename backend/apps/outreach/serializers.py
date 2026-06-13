from rest_framework import serializers
from .models import OutreachEmail

class OutreachEmailSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        model = OutreachEmail
        fields = '__all__'
