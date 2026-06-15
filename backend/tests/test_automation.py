import pytest
from django.test import TestCase
from unittest.mock import patch, Mock, MagicMock
from apps.automation.models import BrowserSession, AutomationRun, AutomationLog
from apps.accounts.models import User, Organization, Membership
from apps.automation.runner import detect_platform
from apps.automation.platforms.base import BasePlatformHandler


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


class PlatformDetectionTests(TestCase):
    def _make_mock_job(self, url='', platform=''):
        job = Mock()
        job.application_page_url = url
        job.apply_url = url
        job.direct_apply_url = url
        job.platform = platform
        return job

    def test_detect_linkedin(self):
        job = self._make_mock_job(url='https://linkedin.com/jobs/view/123')
        self.assertEqual(detect_platform(job), 'linkedin')

    def test_detect_indeed(self):
        job = self._make_mock_job(url='https://indeed.com/viewjob/123')
        self.assertEqual(detect_platform(job), 'indeed')

    def test_detect_greenhouse(self):
        job = self._make_mock_job(url='https://boards.greenhouse.io/acme/jobs/123')
        self.assertEqual(detect_platform(job), 'greenhouse')

    def test_detect_lever(self):
        job = self._make_mock_job(url='https://jobs.lever.co/acme/123')
        self.assertEqual(detect_platform(job), 'lever')

    def test_detect_ashby(self):
        job = self._make_mock_job(url='https://jobs.ashbyhq.com/acme/123')
        self.assertEqual(detect_platform(job), 'ashby')

    def test_detect_workday(self):
        job = self._make_mock_job(url='https://acme.wd5.myworkdayjobs.com/123')
        self.assertEqual(detect_platform(job), 'workday')

    def test_detect_smartrecruiters(self):
        job = self._make_mock_job(url='https://jobs.smartrecruiters.com/acme/123')
        self.assertEqual(detect_platform(job), 'smartrecruiters')

    def test_detect_bamboohr(self):
        job = self._make_mock_job(url='https://acme.bamboohr.com/jobs/123')
        self.assertEqual(detect_platform(job), 'bamboohr')

    def test_detect_generic(self):
        job = self._make_mock_job(url='https://example.com/careers/123')
        self.assertEqual(detect_platform(job), 'generic')

    def test_detect_by_platform_field(self):
        job = self._make_mock_job(url='https://example.com/job', platform='linkedin')
        self.assertEqual(detect_platform(job), 'linkedin')

    def test_detect_no_url(self):
        job = self._make_mock_job(url='')
        self.assertEqual(detect_platform(job), 'generic')


class TestHandler(BasePlatformHandler):
    __test__ = False
    def detect(self):
        return True
    def apply(self):
        return True, self.logs, None


class BaseHandlerTests(TestCase):
    def setUp(self):
        self.page = MagicMock()
        self.context = MagicMock()
        self.info = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1-555-0100',
            'resume_path': '/tmp/test_resume.pdf',
        }

    def test_find_matching_answer_name(self):
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        answer = handler._find_matching_answer('what is your full name?')
        self.assertEqual(answer, 'John Doe')

    def test_find_matching_answer_email(self):
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        answer = handler._find_matching_answer('email address')
        self.assertEqual(answer, 'john@example.com')

    def test_find_matching_answer_phone(self):
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        answer = handler._find_matching_answer('phone number')
        self.assertEqual(answer, '+1-555-0100')

    def test_find_matching_answer_authorization(self):
        info = {**self.info, 'work_authorization': 'US Citizen'}
        handler = TestHandler(self.page, self.context, info, 'cover')
        answer = handler._find_matching_answer('are you authorized to work in the us?')
        self.assertEqual(answer, 'US Citizen')

    def test_find_matching_answer_salary(self):
        info = {**self.info, 'salary_expectation': 'Open to discussion'}
        handler = TestHandler(self.page, self.context, info, 'cover')
        answer = handler._find_matching_answer('what are your salary expectations?')
        self.assertIn('discussion', answer.lower())

    def test_find_matching_answer_start_date(self):
        info = {**self.info, 'availability': 'Immediately'}
        handler = TestHandler(self.page, self.context, info, 'cover')
        answer = handler._find_matching_answer('when can you start?')
        self.assertEqual(answer, 'Immediately')

    def test_find_matching_answer_from_answers_list(self):
        answers = [{'question': 'Do you know Python?', 'answer': 'Yes, 5 years'}]
        handler = TestHandler(self.page, self.context, self.info, 'cover', answers)
        answer = handler._find_matching_answer('do you know python?')
        self.assertEqual(answer, 'Yes, 5 years')

    def test_find_matching_answer_prefer_not_to_say(self):
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        answer = handler._find_matching_answer('what is your gender?')
        self.assertEqual(answer, 'Prefer not to say')

    def test_verify_submission_no_success(self):
        self.page.locator.return_value.count.return_value = 0
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        self.assertFalse(handler.verify_submission())

    def test_detect_captcha_no_match(self):
        self.page.locator.return_value.count.return_value = 0
        handler = TestHandler(self.page, self.context, self.info, 'cover')
        self.assertFalse(handler._detect_captcha())


class PipelineTimeoutTests(TestCase):
    def test_automation_task_timeouts_adequate(self):
        from tasks.automation_tasks import run_application_automation
        self.assertGreaterEqual(run_application_automation.soft_time_limit, 600)
        self.assertGreaterEqual(run_application_automation.time_limit, 1200)

    def test_pipeline_dispatch_timeouts_adequate(self):
        from apps.pipeline.tasks import task_validate_and_dispatch
        self.assertGreaterEqual(task_validate_and_dispatch.soft_time_limit, 600)
        self.assertGreaterEqual(task_validate_and_dispatch.time_limit, 1200)


class ValidationTests(TestCase):
    def test_validate_before_submission_block_no_resume(self):
        from apps.ai.validation_engine import validate_before_submission
        result = validate_before_submission({
            'resume': {},
            'cover_letter': '',
            'answers': [],
            'fit_score': 0,
            'threshold': 70,
            'profile': {},
            'job': {},
        })
        self.assertEqual(result['decision'], 'block')
        self.assertFalse(result['is_valid'])

    def test_validate_before_submission_short_cover_letter(self):
        from apps.ai.validation_engine import validate_before_submission
        result = validate_before_submission({
            'resume': {'adapted_text': 'My adapted resume'},
            'cover_letter': 'Hi',
            'answers': [{'question': 'test', 'answer': 'yes'}],
            'fit_score': 85,
            'threshold': 70,
            'profile': {},
            'job': {},
        })
        self.assertEqual(result['decision'], 'queue_for_review')
