import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from apps.applications.models import Application
from apps.billing.models import UsageEvent

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
    queue='analytics',
)
def generate_daily_analytics():
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    apps = Application.objects.filter(created_at__date=yesterday)
    UsageEvent.objects.create(
        event_type='daily_analytics',
        quantity=apps.count(),
        metadata={
            'date': str(yesterday),
            'submitted': apps.filter(status='submitted').count(),
            'interviews': apps.filter(status='interview').count(),
        }
    )
    return f"Analytics generated for {yesterday}"

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='analytics',
)
def generate_weekly_report(org_id):
    from apps.analytics.services import build_weekly_report
    return build_weekly_report(org_id)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=600,
    acks_late=True,
    queue='analytics',
)
def clean_old_analytics():
    cutoff = timezone.now() - timedelta(days=90)
    UsageEvent.objects.filter(created_at__lt=cutoff).delete()
    return "Cleaned old analytics"
