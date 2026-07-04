import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('ai_job_auto_apply')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'discovery': {'exchange': 'discovery', 'routing_key': 'discovery'},
    'analysis': {'exchange': 'analysis', 'routing_key': 'analysis'},
    'embedding': {'exchange': 'embedding', 'routing_key': 'embedding'},
    'ai': {'exchange': 'ai', 'routing_key': 'ai'},
    'pipeline': {'exchange': 'pipeline', 'routing_key': 'pipeline'},
    'cover_letter': {'exchange': 'cover_letter', 'routing_key': 'cover_letter'},
    'question': {'exchange': 'question', 'routing_key': 'question'},
    'automation': {'exchange': 'automation', 'routing_key': 'automation'},
    'notification': {'exchange': 'notification', 'routing_key': 'notification'},
    'analytics': {'exchange': 'analytics', 'routing_key': 'analytics'},
    'billing': {'exchange': 'billing', 'routing_key': 'billing'},
}

app.conf.task_routes = {
    'tasks.discovery_tasks.*': {'queue': 'discovery'},
    'tasks.analysis_tasks.*': {'queue': 'analysis'},
    'tasks.embedding_tasks.*': {'queue': 'embedding'},
    'apps.ai.tasks.*': {'queue': 'ai'},
    'apps.pipeline.tasks.*': {'queue': 'pipeline'},
    'tasks.cover_letter_tasks.*': {'queue': 'cover_letter'},
    'tasks.question_tasks.*': {'queue': 'question'},
    'tasks.automation_tasks.*': {'queue': 'automation'},
    'tasks.notification_tasks.*': {'queue': 'notification'},
    'tasks.analytics_tasks.*': {'queue': 'analytics'},
    'tasks.billing_tasks.*': {'queue': 'billing'},
}

app.conf.beat_schedule = {
    # Learning engine: decay confidence daily
    'decay-learning-confidence-daily': {
        'task': 'apps.ai.tasks.task_decay_learning_confidence',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'ai'},
    },
    # Learning engine: weekly digest for all active orgs
    'weekly-learning-digest': {
        'task': 'apps.ai.tasks.task_weekly_learning_digest_all',
        'schedule': crontab(hour=8, minute=0, day_of_week='monday'),
        'options': {'queue': 'ai'},
    },
    # Application quality: refresh pending analyses hourly
    'analyze-pending-applications-hourly': {
        'task': 'apps.ai.tasks.task_analyze_pending_applications',
        'schedule': crontab(minute=0),
        'options': {'queue': 'analysis'},
    },
    # Cover letter: batch generate pending cover letters
    'generate-pending-cover-letters': {
        'task': 'apps.ai.tasks.task_generate_pending_cover_letters',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'cover_letter'},
    },
}
