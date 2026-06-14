import pytest
from django.test import TestCase
from unittest.mock import patch, Mock
from apps.automation.models import BrowserSession, AutomationRun, AutomationLog
from apps.accounts.models import User, Organization, Membership


class AutomationModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(email='test@example.com', password='Pass123!', full_name='Test')

    def test_browser_session_creation(self):
        session = BrowserSession.objects.create(organization=self.org, user=self.user, platform='linkedin')
        self.assertEqual(str(session), 'linkedin session (active)')

    def test_browser_session_unique_together(self):
        BrowserSession.objects.create(organization=self.org, user=self.user, platform='linkedin', is_active=True)
        with self.assertRaises(Exception):
            BrowserSession.objects.create(organization=self.org, user=self.user, platform='linkedin', is_active=True)

    def test_automation_run_creation(self):
        run = AutomationRun.objects.create(organization=self.org, started_by=self.user, status='queued')
        self.assertIsNotNone(run.id)
        self.assertEqual(run.status, 'queued')

    def test_automation_log_creation(self):
        run = AutomationRun.objects.create(organization=self.org, started_by=self.user)
        log = AutomationLog.objects.create(automation_run=run, level='info', source='test', message='Test log')
        self.assertIn('Test log', str(log))

    def test_automation_run_status_transition(self):
        run = AutomationRun.objects.create(organization=self.org, started_by=self.user, status='queued')
        run.status = 'running'
        run.save(update_fields=['status'])
        run.refresh_from_db()
        self.assertEqual(run.status, 'running')

    def test_browser_session_error_tracking(self):
        session = BrowserSession.objects.create(organization=self.org, user=self.user, platform='linkedin')
        session.error_count = 3
        session.last_error = 'Connection timeout'
        session.status = 'error'
        session.save(update_fields=['error_count', 'last_error', 'status'])
        session.refresh_from_db()
        self.assertEqual(session.error_count, 3)
        self.assertEqual(session.status, 'error')


class PlaywrightCleanupTests(TestCase):
    def test_automation_task_timeouts_adequate(self):
        from tasks.automation_tasks import run_application_automation
        self.assertGreaterEqual(run_application_automation.soft_time_limit, 600)
        self.assertGreaterEqual(run_application_automation.time_limit, 1200)

    def test_pipeline_dispatch_timeouts_adequate(self):
        from apps.pipeline.tasks import task_dispatch_application_auto
        self.assertGreaterEqual(task_dispatch_application_auto.soft_time_limit, 600)
        self.assertGreaterEqual(task_dispatch_application_auto.time_limit, 1200)
