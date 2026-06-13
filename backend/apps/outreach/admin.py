from django.contrib import admin
from .models import OutreachEmail

@admin.register(OutreachEmail)
class OutreachEmailAdmin(admin.ModelAdmin):
    list_display = ('business', 'campaign', 'status', 'generated_at', 'sent_at', 'reply_received')
    list_filter = ('status', 'reply_received', 'campaign')
