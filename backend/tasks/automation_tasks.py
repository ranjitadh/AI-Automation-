import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from apps.applications.models import Application, ApplicationEvent
from apps.automation.models import AutomationRun, AutomationLog
from apps.automation.runner import run_automation

logger = logging.getLogger(__name__)

@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=600,
    time_limit=1200,
    acks_late=True,
    queue='automation',
)
def run_application_automation(application_id):
    try:
        app = Application.objects.get(id=application_id)
    except ObjectDoesNotExist:
        logger.error(f"Application {application_id} not found")
        return False
    run = AutomationRun.objects.create(
        organization=app.organization,
        application=app,
        campaign=app.campaign,
        status='running',
        started_at=timezone.now(),
    )
    AutomationLog.objects.create(
        automation_run=run,
        level='info',
        source='system',
        message=f"Starting automation for {app.job.title} @ {app.job.company.name}",
    )

    app.dispatch_status = 'running'
    app.dispatch_attempts += 1
    app.save(update_fields=['dispatch_status', 'dispatch_attempts'])

    logs = []
    success = False
    try:
        success, logs, screenshot_path = run_automation(app.job, app.cover_letter)
        run.duration_ms = int((timezone.now() - run.started_at).total_seconds() * 1000)
        for log_entry in logs:
            AutomationLog.objects.create(automation_run=run, level='info', source='playwright', message=log_entry)
        if success:
            app.status = 'submitted'
            app.submitted_at = timezone.now()
            app.dispatch_status = 'success'
            run.status = 'completed'
            ApplicationEvent.objects.create(application=app, event_type='submitted')
            if screenshot_path:
                app.confirmation_text = "Submission confirmed"
        else:
            app.dispatch_status = 'failed' if app.dispatch_attempts >= 3 else 'retrying'
            run.status = 'failed' if app.dispatch_attempts >= 3 else 'running'
            AutomationLog.objects.create(automation_run=run, level='error', source='system', message='Automation failed')
    except Exception as e:
        app.dispatch_status = 'failed'
        run.status = 'failed'
        AutomationLog.objects.create(automation_run=run, level='error', source='system', message=str(e))
        logger.error(f"Automation error for {app.id}: {e}")

    run.completed_at = timezone.now()
    run.save(update_fields=['status', 'completed_at', 'duration_ms'])
    app.dispatch_log = '\n'.join(logs) if logs else ''
    app.save(update_fields=['status', 'submitted_at', 'dispatch_status', 'dispatch_log', 'confirmation_text'])
    return success


