import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from apps.notifications.models import Notification
from apps.notifications.services import send_email, send_slack, send_discord, send_webhook

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
    queue='notification',
)
def send_notification_task(notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
    except ObjectDoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return False
    try:
        if notification.channel == 'email':
            send_email(notification)
        elif notification.channel == 'slack':
            send_slack(notification)
        elif notification.channel == 'discord':
            send_discord(notification)
        elif notification.channel == 'webhook':
            send_webhook(notification)
        return True
    except Exception as e:
        logger.error(f"Failed to send notification {notification_id}: {e}")
        return False


