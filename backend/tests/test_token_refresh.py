import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class TokenRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()
        self.user = User.objects.create_user(email='test@example.com', password='Pass123!', full_name='Test')
        self.org = Organization.objects.create(name='Test Org')
        Membership.objects.create(user=self.user, organization=self.org, role='owner')

    def tearDown(self):
        self._throttle_patch.stop()

    def test_token_refresh_endpoint_exists(self):
        url = reverse('auth-token-refresh')
        self.assertIsNotNone(url)

    def test_token_refresh_success(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth-token-refresh')
        resp = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

    def test_token_refresh_with_invalid_token(self):
        url = reverse('auth-token-refresh')
        resp = self.client.post(url, {'refresh': 'invalid-token'})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_blacklists_old_token(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth-token-refresh')
        resp1 = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        resp2 = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(resp2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_returns_new_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse('auth-token-refresh')
        resp = self.client.post(url, {'refresh': str(refresh)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', resp.data)
