import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.automation.models import BrowserSession, AutomationRun, AutomationLog
from apps.audit.models import AuditLog

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
    queue='default',
)
def cleanup_old_data():
    cutoff = timezone.now() - timedelta(days=90)
    AuditLog.objects.filter(timestamp__lt=cutoff).delete()
    AutomationRun.objects.filter(created_at__lt=cutoff, status__in=['completed', 'failed', 'canceled']).delete()
    AutomationLog.objects.filter(created_at__lt=cutoff).delete()
    BrowserSession.objects.filter(last_used_at__lt=cutoff, is_active=False).delete()
    return "Cleanup complete"

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='default',
)
def health_check():
    logger.info("Health check OK")
    return "OK"
