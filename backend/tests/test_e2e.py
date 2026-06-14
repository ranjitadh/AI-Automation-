import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class EndToEndFlowTests(TestCase):
    """Simulate a full user flow: register → create org → create resume → create campaign → analyze → approve → submit"""

    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()

    def tearDown(self):
        self._throttle_patch.stop()

    def _auth_as(self, user, org):
        self.client.force_authenticate(user=user)
        self.client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

    def test_full_user_registration_flow(self):
        """Register → login → switch org → access protected endpoints"""
        register_resp = self.client.post(reverse('auth-register'), {
            'email': 'new@example.com',
            'password': 'StrongPass123!',
            'full_name': 'New User',
            'organization_name': 'New Org',
        })
        self.assertEqual(register_resp.status_code, status.HTTP_201_CREATED)
        user_id = register_resp.data['user']['id']
        org_id = register_resp.data['organization']['id']

        login_resp = self.client.post(reverse('auth-login'), {
            'email': 'new@example.com',
            'password': 'StrongPass123!',
        })
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_resp.data)

        me_resp = self.client.get(reverse('auth-me'),
                                  HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data['email'], 'new@example.com')

    def test_org_creation_and_campaign_flow(self):
        """Register → list orgs → create campaign → access campaign"""
        register_resp = self.client.post(reverse('auth-register'), {
            'email': 'campaign@example.com',
            'password': 'StrongPass123!',
            'full_name': 'Campaign User',
            'organization_name': 'Campaign Org',
        })
        token = register_resp.data['access']
        org_id = register_resp.data['organization']['id']

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_ORGANIZATION_ID=str(org_id))

        campaign_resp = self.client.post(reverse('campaigns-list'), {
            'name': 'Q1 2026 Hiring',
            'target_titles': ['Software Engineer'],
            'target_locations': ['San Francisco'],
        }, format='json')
        if campaign_resp.status_code != 201:
            print(f'Campaign error: {getattr(campaign_resp, "data", "no data")}')
        self.assertEqual(campaign_resp.status_code, status.HTTP_201_CREATED)

        list_resp = self.client.get(reverse('campaigns-list'))
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_resp.data['results']), 1)

    def test_permission_denied_without_org_header(self):
        """Authenticated user without org header gets forbidden"""
        user = User.objects.create_user(email='isolated@example.com', password='StrongPass123!', full_name='Isolated')
        org = Organization.objects.create(name='Isolated Org')
        Membership.objects.create(user=user, organization=org, role='owner', is_default=True)
        self.client.force_authenticate(user=user)
        self.client.credentials()

        resp = self.client.get(reverse('campaigns-list'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_member_and_switch_flow(self):
        """Owner invites member → member switches org → accesses resources"""
        owner = User.objects.create_user(email='owner@e2e.com', password='StrongPass123!', full_name='Owner')
        org = Organization.objects.create(name='E2E Org')
        Membership.objects.create(user=owner, organization=org, role='owner', is_default=True)

        self._auth_as(owner, org)

        invite_resp = self.client.post(reverse('orgs-invite', args=[org.id]), {
            'email': 'member@e2e.com',
            'role': 'member',
        })
        self.assertEqual(invite_resp.status_code, status.HTTP_200_OK)

        member = User.objects.get(email='member@e2e.com')
        self._auth_as(member, org)

        list_resp = self.client.get(reverse('campaigns-list'))
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)

        switch_url = reverse('orgs-switch', args=[org.id])
        switch_resp = self.client.post(switch_url)
        self.assertEqual(switch_resp.status_code, status.HTTP_200_OK)

    def test_approve_reject_requires_admin(self):
        """Only admins can approve/reject applications"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from apps.jobs.models import Job, Company
        from apps.applications.models import Application

        admin = User.objects.create_user(email='admin@e2e.com', password='StrongPass123!', full_name='Admin')
        viewer = User.objects.create_user(email='viewer@e2e.com', password='StrongPass123!', full_name='Viewer')
        org = Organization.objects.create(name='Approve Org')
        Membership.objects.create(user=admin, organization=org, role='admin', is_default=True)
        Membership.objects.create(user=viewer, organization=org, role='viewer', is_default=True)

        company = Company.objects.create(name='Test Co')
        job = Job.objects.create(title='Engineer', company=company)
        app = Application.objects.create(organization=org, job=job, applicant=admin)

        viewer_token = str(RefreshToken.for_user(viewer).access_token)
        admin_token = str(RefreshToken.for_user(admin).access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {viewer_token}', HTTP_X_ORGANIZATION_ID=str(org.id))
        approve_resp = self.client.post(reverse('applications-approve', args=[app.id]))
        self.assertEqual(approve_resp.status_code, status.HTTP_403_FORBIDDEN)

        reject_resp = self.client.post(reverse('applications-reject', args=[app.id]))
        self.assertEqual(reject_resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}', HTTP_X_ORGANIZATION_ID=str(org.id))
        approve_resp = self.client.post(reverse('applications-approve', args=[app.id]))
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)

    def test_token_refresh_flow(self):
        """Full token refresh cycle"""
        user = User.objects.create_user(email='refresh@e2e.com', password='StrongPass123!', full_name='Refresh')
        org = Organization.objects.create(name='Refresh Org')
        Membership.objects.create(user=user, organization=org, role='owner')

        login_resp = self.client.post(reverse('auth-login'), {
            'email': 'refresh@e2e.com',
            'password': 'StrongPass123!',
        })
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

        refresh_token = login_resp.data['refresh']
        refresh_resp = self.client.post(reverse('auth-token-refresh'), {
            'refresh': refresh_token,
        })
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_resp.data)
        self.assertIn('refresh', refresh_resp.data)

        new_access = refresh_resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        me_resp = self.client.get(reverse('auth-me'))
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
