from rest_framework import serializers
from .models import PipelineRun

class PipelineRunSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source='business.name', read_only=True)

    class Meta:
        model = PipelineRun
        fields = '__all__'
