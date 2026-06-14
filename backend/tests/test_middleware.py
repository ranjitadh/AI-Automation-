import pytest
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class CSPMiddlewareTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_csp_header_present(self):
        resp = self.client.get('/health/')
        self.assertIn('Content-Security-Policy', resp.headers)
        csp = resp.headers['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertIn("form-action 'self'", csp)

    def test_csp_prevents_inline_scripts(self):
        resp = self.client.get('/health/')
        csp = resp.headers['Content-Security-Policy']
        self.assertNotIn("script-src 'unsafe-inline'", csp.split(';')[1])


class OrgMiddlewareTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()
        self.user = User.objects.create_user(email='test@example.com', password='Pass123!', full_name='Test')
        self.org = Organization.objects.create(name='Test Org')
        Membership.objects.create(user=self.user, organization=self.org, role='owner', is_default=True)

    def tearDown(self):
        self._throttle_patch.stop()

    def test_org_middleware_sets_request_org(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/health/', HTTP_X_ORGANIZATION_ID=str(self.org.id))
        self.assertEqual(resp.status_code, 200)

    def test_org_middleware_no_header(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)

    def test_org_middleware_invalid_org_id(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/health/', HTTP_X_ORGANIZATION_ID='00000000-0000-0000-0000-000000000000')
        self.assertEqual(resp.status_code, 200)

    def test_org_middleware_not_member(self):
        other_org = Organization.objects.create(name='Other Org')
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/health/', HTTP_X_ORGANIZATION_ID=str(other_org.id))
        self.assertEqual(resp.status_code, 200)
