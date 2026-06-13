from django.contrib import admin
from .models import Campaign

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_by', 'target_category', 'created_at')
    list_filter = ('status', 'target_category')
