from django.db import models
from apps.common.models import TimeStampedMixin
import uuid

class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    max_applications_monthly = models.IntegerField(default=10)
    max_resumes = models.IntegerField(default=2)
    max_team_members = models.IntegerField(default=1)
    has_ats_optimization = models.BooleanField(default=False)
    has_auto_apply = models.BooleanField(default=False)
    has_analytics = models.CharField(max_length=20, choices=(
        ('none', 'None'),
        ('basic', 'Basic'),
        ('advanced', 'Advanced'),
        ('full', 'Full'),
    ), default='basic')
    has_api_access = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    features = models.JSONField(default=dict, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"

class Subscription(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='subscriptions', db_index=True)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, related_name='subscriptions', db_index=True)
    status = models.CharField(max_length=20, choices=(
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    ), default='active', db_index=True)
    billing_cycle = models.CharField(max_length=20, choices=(
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ), default='monthly')
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['organization', 'plan']

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name if self.plan else 'No Plan'}"

class Invoice(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='invoices', db_index=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='invoices', db_index=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('void', 'Void'),
    ), default='draft', db_index=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id} - ${self.amount}"

class UsageEvent(TimeStampedMixin):
    organization = models.ForeignKey('accounts.Organization', on_delete=models.CASCADE, related_name='usage_events', db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='usage_events', db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    quantity = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'event_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} x{self.quantity}"
