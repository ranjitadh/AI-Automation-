import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from apps.billing.models import Subscription

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


