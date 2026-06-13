from django.db import models
from apps.businesses.models import Business
from apps.campaigns.models import Campaign
import uuid

class OutreachEmail(models.Model):
    STATUS_CHOICES = (
        ('generated', 'Generated'),
        ('sent', 'Sent'),
        ('replied', 'Replied'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='emails')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='emails')
    
    subject = models.CharField(max_length=255)
    email_body = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    reply_received = models.BooleanField(default=False)
    reply_content = models.TextField(null=True, blank=True)
    
    # Auto-dispatch (Direct Apply) automation fields
    dispatch_status = models.CharField(
        max_length=20, 
        choices=(
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('success', 'Success'),
            ('failed', 'Failed')
        ), 
        default='pending'
    )
    dispatch_log = models.TextField(blank=True, null=True)
    screenshot = models.ImageField(upload_to='outreach_screenshots/', blank=True, null=True)

    def __str__(self):
        return f"Email for {self.business.name} - {self.status}"
