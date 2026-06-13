from django.db import models
import uuid

class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    
    website_url = models.URLField(max_length=500, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    social_media = models.JSONField(default=dict, blank=True)
    
    google_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    google_description = models.TextField(blank=True, null=True)
    
    # Auto-detected presence
    has_website = models.BooleanField(default=False)
    has_booking_system = models.BooleanField(default=False)
    
    # AI Analysis
    digital_score = models.IntegerField(default=0)  # 0 to 100
    analysis_notes = models.JSONField(default=dict, blank=True)
    auto_apply = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.category})"
