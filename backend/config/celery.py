import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('ai_job_auto_apply')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'discovery': {'exchange': 'discovery', 'routing_key': 'discovery'},
    'analysis': {'exchange': 'analysis', 'routing_key': 'analysis'},
    'embedding': {'exchange': 'embedding', 'routing_key': 'embedding'},
    'resume': {'exchange': 'resume', 'routing_key': 'resume'},
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
    'tasks.resume_tasks.*': {'queue': 'resume'},
    'tasks.cover_letter_tasks.*': {'queue': 'cover_letter'},
    'tasks.question_tasks.*': {'queue': 'question'},
    'tasks.automation_tasks.*': {'queue': 'automation'},
    'tasks.notification_tasks.*': {'queue': 'notification'},
    'tasks.analytics_tasks.*': {'queue': 'analytics'},
    'tasks.billing_tasks.*': {'queue': 'billing'},
}
