from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedMixin

class Interview(TimeStampedMixin):
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='interviews', db_index=True)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='interviews', db_index=True)

    interview_type = models.CharField(max_length=50, choices=(
        ('phone', 'Phone Screen'),
        ('video', 'Video Call'),
        ('onsite', 'On-Site'),
        ('technical', 'Technical'),
        ('final', 'Final Round'),
        ('take_home', 'Take Home'),
        ('group', 'Group Interview'),
    ), db_index=True)
    round = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=(
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('rescheduled', 'Rescheduled'),
        ('no_show', 'No Show'),
    ), default='scheduled', db_index=True)

    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    completed_at = models.DateTimeField(null=True, blank=True)

    interviewers = models.JSONField(default=list, blank=True)
    feedback = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    follow_up_action = models.TextField(blank=True)
    follow_up_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_at']
        unique_together = ['application', 'round']

    def __str__(self):
        return f"{self.interview_type} round {self.round} for {self.application.job.title}"

class Offer(TimeStampedMixin):
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='offers', db_index=True)
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='offers', db_index=True)

    status = models.CharField(max_length=20, choices=(
        ('negotiating', 'Negotiating'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
    ), default='negotiating', db_index=True)

    base_salary = models.IntegerField(null=True, blank=True)
    bonus = models.IntegerField(null=True, blank=True)
    equity = models.CharField(max_length=100, blank=True)
    signing_bonus = models.IntegerField(null=True, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    start_date = models.DateField(null=True, blank=True)
    relocation_package = models.TextField(blank=True)

    offer_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)

    counter_offer_amount = models.IntegerField(null=True, blank=True)
    counter_offer_details = models.TextField(blank=True)
    negotiation_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-offer_date']
        unique_together = ['application', 'organization']

    def __str__(self):
        return f"Offer for {self.application.job.title} - {self.status}"
