from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class Recruiter(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, null=True, blank=True, related_name='recruiters', db_index=True)
    company = models.ForeignKey('jobs.Company', on_delete=models.CASCADE, related_name='recruiters', db_index=True)
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    linkedin_url = models.TextField(blank=True)
    avatar_url = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['company', 'email']

    def __str__(self):
        return f"{self.name} @ {self.company.name}"

class RecruiterOutreach(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='outreaches', db_index=True)
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='outreaches', db_index=True)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='outreaches', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='outreaches', db_index=True)

    message_type = models.CharField(max_length=20, choices=(
        ('initial', 'Initial'),
        ('follow_up', 'Follow Up'),
        ('thank_you', 'Thank You'),
        ('networking', 'Networking'),
    ), default='initial', db_index=True)
    subject = models.CharField(max_length=500, blank=True)
    content = models.TextField()

    status = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('replied', 'Replied'),
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('rejected', 'Rejected'),
    ), default='draft', db_index=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.message_type} to {self.recruiter.name}"
