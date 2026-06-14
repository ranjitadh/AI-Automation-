from django.contrib import admin
from .models import OrganizationSettings, Skill, FileUpload


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    list_display = ['organization', 'default_timezone', 'default_locale', 'updated_at']
    search_fields = ['organization__name']
    readonly_fields = ['created_at', 'updated_at']

    def linkedin_password_display(self, obj):
        return '********' if obj.linkedin_password else ''
    linkedin_password_display.short_description = 'linkedin_password'

    def indeed_password_display(self, obj):
        return '********' if obj.indeed_password else ''
    indeed_password_display.short_description = 'indeed_password'

    def get_fields(self, request, obj=None):
        fields = [f.name for f in self.model._meta.get_fields() if f.name not in ('linkedin_password', 'indeed_password')]
        fields.extend(['linkedin_password_display', 'indeed_password_display'])
        return fields


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_verified']
    search_fields = ['name', 'category']
    list_filter = ['category', 'is_verified']


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['filename', 'original_filename', 'file_type', 'organization', 'created_at']
    search_fields = ['filename', 'original_filename']
    list_filter = ['file_type', 'storage_provider']
    readonly_fields = ['checksum', 'created_at', 'updated_at']
