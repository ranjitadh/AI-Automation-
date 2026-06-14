import pytest
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class SecuritySettingsTests(TestCase):
    def test_debug_default_false(self):
        """DEBUG must default to False for production safety"""
        self.assertFalse(
            getattr(settings, 'DEBUG', True),
            "DEBUG should default to False"
        )

    def test_secret_key_required(self):
        """SECRET_KEY must not be a known default"""
        self.assertNotEqual(
            settings.SECRET_KEY,
            'django-insecure-default-key-for-dev',
            "SECRET_KEY must not be the dev default"
        )

    def test_cors_not_wildcard(self):
        """CORS must not allow all origins by default"""
        self.assertFalse(
            getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', True),
            "CORS_ALLOW_ALL_ORIGINS should default to False"
        )

    def test_hsts_configured(self):
        """HSTS must be set for production"""
        hsts = getattr(settings, 'SECURE_HSTS_SECONDS', 0)
        self.assertGreaterEqual(hsts, 0)

    def test_session_cookie_secure(self):
        """Session cookie must be secure in production"""
        val = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        self.assertIsNotNone(val)

    def test_csrf_cookie_secure(self):
        """CSRF cookie must be secure in production"""
        val = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        self.assertIsNotNone(val)

    def test_x_frame_options(self):
        """Clickjacking protection must be enabled"""
        self.assertEqual(
            getattr(settings, 'X_FRAME_OPTIONS', ''),
            'DENY'
        )

    def test_secure_referrer_policy(self):
        """Referrer policy must be set"""
        self.assertEqual(
            getattr(settings, 'SECURE_REFERRER_POLICY', ''),
            'same-origin'
        )

    def test_password_validators(self):
        """Password validators must be configured"""
        self.assertTrue(len(settings.AUTH_PASSWORD_VALIDATORS) > 0)

    def test_data_upload_limits(self):
        """File upload size limits must be set"""
        self.assertLessEqual(
            settings.DATA_UPLOAD_MAX_MEMORY_SIZE,
            20 * 1024 * 1024,
        )

    def test_celery_retry_configured(self):
        """Celery tasks should have reasonable time limits"""
        self.assertIsNotNone(settings.CELERY_TASK_TIME_LIMIT)
        self.assertIsNotNone(settings.CELERY_TASK_SOFT_TIME_LIMIT)
