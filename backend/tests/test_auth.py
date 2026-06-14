import pytest
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.me_url = reverse('auth-me')
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()

    def tearDown(self):
        self._throttle_patch.stop()

    def test_register_success(self):
        resp = self.client.post(self.register_url, {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'full_name': 'Test User',
            'organization_name': 'Test Org',
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(email='dup@example.com', password='Pass123!', full_name='Dup')
        resp = self.client.post(self.register_url, {
            'email': 'dup@example.com',
            'password': 'StrongPass123!',
            'full_name': 'Test User',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        User.objects.create_user(email='login@example.com', password='Pass123!', full_name='Login')
        resp = self.client.post(self.login_url, {
            'email': 'login@example.com',
            'password': 'Pass123!',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

    def test_login_wrong_password(self):
        User.objects.create_user(email='wrong@example.com', password='Pass123!', full_name='Wrong')
        resp = self.client.post(self.login_url, {
            'email': 'wrong@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_authenticated(self):
        user = User.objects.create_user(email='me@example.com', password='Pass123!', full_name='Me')
        org = Organization.objects.create(name='My Org')
        Membership.objects.create(user=user, organization=org, role='owner')
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['email'], 'me@example.com')

    def test_me_unauthenticated(self):
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
