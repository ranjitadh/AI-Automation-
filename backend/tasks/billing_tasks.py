import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.billing.models import Subscription, Invoice
from apps.accounts.models import Organization

logger = logging.getLogger(__name__)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='billing',
)
def sync_subscription_to_stripe(subscription_id):
    try:
        sub = Subscription.objects.get(id=subscription_id)
    except ObjectDoesNotExist:
        logger.error(f"Subscription {subscription_id} not found")
        return False
    logger.info(f"Syncing subscription {sub.id} to Stripe")
    return True

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='billing',
)
def handle_stripe_webhook(event_type, data):
    logger.info(f"Processing Stripe webhook: {event_type}")
    return True

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='billing',
)
def check_expired_subscriptions():
    expired = Subscription.objects.filter(
        status='active',
        current_period_end__lt=timezone.now(),
    )
    for sub in expired:
        sub.status = 'expired'
        sub.save(update_fields=['status'])
    return f"Expired {expired.count()} subscriptions"

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='billing',
)
def generate_monthly_invoices():
    today = timezone.now()
    if today.day != 1:
        return "Not first of month"
    active_subs = Subscription.objects.filter(status='active').select_related('organization', 'plan')
    for sub in active_subs:
        Invoice.objects.create(
            organization=sub.organization,
            subscription=sub,
            amount=sub.plan.price_monthly if sub.plan else 0,
            status='open',
            period_start=sub.current_period_start,
            period_end=sub.current_period_end,
        )
    return f"Generated {active_subs.count()} invoices"
