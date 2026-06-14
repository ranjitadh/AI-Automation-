from rest_framework import serializers
from .models import FileUpload, OrganizationSettings, Skill


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUpload
        fields = [
            'id', 'filename', 'original_filename', 'file_type', 'file_size',
            'storage_path', 'storage_bucket', 'storage_provider', 'checksum',
            'is_public', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'file_size', 'checksum']


class OrganizationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSettings
        exclude = ['linkedin_password', 'indeed_password']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('id', 'name', 'normalized_name', 'category', 'aliases', 'is_verified', 'created_at')
