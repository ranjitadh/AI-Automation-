import os

os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production')
os.environ.setdefault('DB_PASSWORD', 'test')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-placeholder')
os.environ.setdefault('STRIPE_API_KEY', 'sk_test_placeholder')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'whsec_test')
os.environ.setdefault('ENCRYPTION_KEY', 'uW7Byj3kHNgb3EtZLw9rsPs4ZCJyOo2QgqojEhuW7mw=')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('ALLOWED_HOSTS', 'localhost,127.0.0.1')
os.environ.setdefault('SENTRY_DSN', '')
os.environ.setdefault('EMAIL_BACKEND', 'django.core.mail.backends.locmem.EmailBackend')

from .settings import *  # noqa

# Disable throttling for tests
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100000/hour',
    'user': '100000/hour',
}

# Override VectorField to use JSONField for SQLite tests
from pgvector.django import VectorField
from django.db import models

original_init = VectorField.__init__
def patched_init(self, *args, **kwargs):
    kwargs.pop('dimensions', None)
    original_init(self, *args, **kwargs)
VectorField.__init__ = patched_init

original_db_type = VectorField.db_type
def patched_db_type(self, connection):
    return 'text'
VectorField.db_type = patched_db_type

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for tests
MIGRATION_MODULES = {app.split('.')[-1] if '.' in app else app: None
                     for app in INSTALLED_APPS if app not in ('django.contrib.admin', 'django.contrib.auth')}
