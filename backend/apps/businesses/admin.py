from django.contrib import admin
from .models import Business

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'location', 'digital_score', 'has_website')
    search_fields = ('name', 'category', 'location')
    list_filter = ('category', 'has_website')
