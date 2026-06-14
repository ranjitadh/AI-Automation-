import pytest
from django.test import TestCase
from unittest.mock import patch, Mock
from apps.pipeline.utils import _call_gpt, _count_tokens
from apps.pipeline.tasks import start_pipeline_for_job
from apps.jobs.models import Job, Company, JobSource
from apps.accounts.models import Organization
from django.conf import settings


class PipelineUtilsTests(TestCase):
    def test_count_tokens_uses_tiktoken(self):
        text = "Hello, this is a test sentence for token counting."
        count = _count_tokens(text)
        self.assertGreater(count, 0)
        self.assertIsInstance(count, int)

    def test_count_tokens_fallback_on_error(self):
        count = _count_tokens("")
        self.assertEqual(count, 0)

    @patch('apps.pipeline.utils.client')
    def test_call_gpt_returns_json(self, mock_client):
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"key": "value"}'))]
        mock_client.chat.completions.create.return_value = mock_response
        with patch('apps.pipeline.utils.check_daily_budget', return_value=True):
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {"key": "value"})

    @patch('apps.pipeline.utils.client')
    def test_call_gpt_handles_rate_limit(self, mock_client):
        from openai import RateLimitError
        mock_client.chat.completions.create.side_effect = RateLimitError("rate limited", response=Mock(status_code=429), body={})
        with patch('apps.pipeline.utils.check_daily_budget', return_value=True):
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {})

    @patch('apps.pipeline.utils.client')
    def test_call_gpt_handles_timeout(self, mock_client):
        from openai import APITimeoutError
        mock_client.chat.completions.create.side_effect = APITimeoutError("timeout")
        with patch('apps.pipeline.utils.check_daily_budget', return_value=True):
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {})

    @patch('apps.pipeline.utils.client')
    def test_call_gpt_handles_api_error(self, mock_client):
        from openai import APIError
        mock_client.chat.completions.create.side_effect = APIError("api error", request=Mock(), body={})
        with patch('apps.pipeline.utils.check_daily_budget', return_value=True):
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {})

    @patch('apps.pipeline.utils.check_daily_budget', return_value=False)
    def test_call_gpt_respects_budget(self, mock_budget):
        with patch('apps.pipeline.utils.client') as mock_client:
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {})
        mock_client.chat.completions.create.assert_not_called()

    def test_call_gpt_no_client(self):
        with patch('apps.pipeline.utils.client', None):
            result = _call_gpt("system", "prompt")
        self.assertEqual(result, {})


class PipelineTaskTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Test Org')
        self.source = JobSource.objects.create(organization=self.org, name='Test Source', connector_type='api')
        self.company = Company.objects.create(name='Test Co')
        self.job = Job.objects.create(title='Engineer', company=self.company, source=self.source)

    def test_start_pipeline_for_job_creates_run(self):
        from apps.jobs.models import Job as JobModel
        with patch.object(JobModel, 'auto_apply', False, create=True):
            run_id = start_pipeline_for_job(str(self.job.id), org_id=str(self.org.id))
        self.assertIsNotNone(run_id)

    def test_start_pipeline_for_job_missing_job(self):
        run_id = start_pipeline_for_job('00000000-0000-0000-0000-000000000000')
        self.assertIsNone(run_id)

    def test_start_pipeline_for_job_no_org(self):
        job_no_source = Job.objects.create(title='No Source', company=self.company)
        run_id = start_pipeline_for_job(str(job_no_source.id))
        self.assertIsNone(run_id)

    def test_analyze_job_fit_returns_dict(self):
        from apps.pipeline.utils import analyze_job_fit
        setattr(self.job, 'job_description_text', 'We need a Python developer with AWS experience.')
        setattr(self.job, 'location', 'San Francisco')
        with patch('apps.pipeline.utils._call_gpt', return_value={"score": 75, "strengths": ["Python"], "gaps": ["AWS"], "key_requirements": []}):
            result = analyze_job_fit(self.job)
        self.assertIn('score', result)
        self.assertEqual(result['score'], 75)

    def test_generate_cover_letter_returns_dict(self):
        from apps.pipeline.utils import generate_cover_letter
        setattr(self.job, 'job_description_text', 'We need a Python developer.')
        with patch('apps.pipeline.utils._call_gpt', return_value={"subject": "Application", "cover_letter": "Dear Sir"}):
            result = generate_cover_letter(self.job)
        self.assertIn('subject', result)
        self.assertIn('cover_letter', result)
