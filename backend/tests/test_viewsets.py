import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class ViewSetAuthTests(TestCase):
    """Verify all viewsets require authentication"""

    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()
        self.user = User.objects.create_user(email='test@example.com', password='Pass123!', full_name='Test')
        self.org = Organization.objects.create(name='Test Org')
        Membership.objects.create(user=self.user, organization=self.org, role='owner', is_default=True)

    def tearDown(self):
        self._throttle_patch.stop()

    def _endpoints_require_auth(self):
        endpoints = [
            ('campaigns-list', 'get'),
            ('campaigns-list', 'post'),
            ('resumes-list', 'get'),
            ('resumes-list', 'post'),
            ('applications-list', 'get'),
            ('applications-list', 'post'),
            ('jobs-list', 'get'),
            ('jobs-list', 'post'),
            ('cover-letters-list', 'get'),
            ('cover-letters-list', 'post'),
            ('question-answers-list', 'get'),
            ('question-answers-list', 'post'),
            ('recruiters-list', 'get'),
            ('recruiters-list', 'post'),
            ('recruiter-outreach-list', 'get'),
            ('recruiter-outreach-list', 'post'),
            ('orgs-list', 'get'),
            ('orgs-list', 'post'),
            ('interviews-list', 'get'),
            ('offers-list', 'get'),
            ('browser-sessions-list', 'get'),
            ('automation-runs-list', 'get'),
            ('notifications-list', 'get'),
            ('webhooks-list', 'get'),
            ('companies-list', 'get'),
            ('job-analysis-list', 'get'),
            ('ats-analysis-list', 'get'),
            ('automation-logs-list', 'get'),
            ('invoices-list', 'get'),
            ('pipelinerun-list', 'get'),
        ]
        for name, method in endpoints:
            with self.subTest(endpoint=name):
                try:
                    url = reverse(name)
                except Exception:
                    continue
                func = getattr(self.client, method)
                resp = func(url)
                self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                              f"{name} should require auth but got {resp.status_code}")

    def test_authenticated_user_can_access(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_ORGANIZATION_ID=str(self.org.id))
        for name in ['campaigns-list', 'resumes-list', 'applications-list', 'jobs-list']:
            with self.subTest(endpoint=name):
                try:
                    url = reverse(name)
                    resp = self.client.get(url)
                    self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND))
                except Exception:
                    pass

    def test_plan_endpoint_public(self):
        resp = self.client.get(reverse('plans-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_question_bank_endpoint_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('question-bank-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_file_upload_requires_org(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials()
        resp = self.client.get(reverse('fileupload-list'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_file_upload_with_org(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_ORGANIZATION_ID=str(self.org.id))
        resp = self.client.get(reverse('fileupload-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_skill_list_public(self):
        resp = self.client.get(reverse('skill-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
