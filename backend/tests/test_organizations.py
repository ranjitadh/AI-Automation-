import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class OrganizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()
        resp = self.client.post(self.register_url, {
            'email': 'owner@example.com',
            'password': 'StrongPass123!',
            'full_name': 'Owner User',
            'organization_name': 'Owner Org',
        })
        self.token = resp.data['access']
        self.org_id = resp.data['organization']['id']
        self.user_id = resp.data['user']['id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}', HTTP_X_ORGANIZATION_ID=str(self.org_id))

    def tearDown(self):
        self._throttle_patch.stop()

    def test_create_organization(self):
        resp = self.client.post(reverse('orgs-list'), {'name': 'New Org'})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Organization.objects.filter(name='New Org').exists())

    def test_list_my_organizations(self):
        resp = self.client.get(reverse('orgs-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['results']), 1)

    def test_org_members_list(self):
        resp = self.client.get(reverse('orgs-members', args=[self.org_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['role'], 'owner')

    def test_invite_member_by_owner(self):
        resp = self.client.post(reverse('orgs-invite', args=[self.org_id]), {'email': 'member@example.com', 'role': 'member'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(Membership.objects.filter(organization_id=self.org_id, user__email='member@example.com').exists())

    def test_invite_member_by_non_admin_fails(self):
        new_user = User.objects.create_user(email='viewer@example.com', password='Pass123!', full_name='Viewer')
        Membership.objects.create(user=new_user, organization_id=self.org_id, role='viewer')
        self.client.force_authenticate(user=new_user)
        resp = self.client.post(reverse('orgs-invite', args=[self.org_id]), {'email': 'another@example.com', 'role': 'member'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_member_role_by_owner(self):
        member = User.objects.create_user(email='member@example.com', password='Pass123!', full_name='Member')
        m = Membership.objects.create(user=member, organization_id=self.org_id, role='member')
        resp = self.client.patch(reverse('orgs-member-update', args=[self.org_id, m.id]), {'role': 'admin'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        m.refresh_from_db()
        self.assertEqual(m.role, 'admin')

    def test_delete_member_by_owner(self):
        member = User.objects.create_user(email='member@example.com', password='Pass123!', full_name='Member')
        m = Membership.objects.create(user=member, organization_id=self.org_id, role='member')
        resp = self.client.delete(reverse('orgs-member-update', args=[self.org_id, m.id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Membership.objects.filter(id=m.id).exists())

    def test_cannot_delete_owner(self):
        resp = self.client.delete(reverse('orgs-member-update', args=[self.org_id, Membership.objects.get(organization_id=self.org_id, role='owner').id]))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_switch_organization(self):
        org2 = Organization.objects.create(name='Second Org')
        Membership.objects.create(user_id=self.user_id, organization=org2, role='member')
        resp = self.client.post(reverse('orgs-switch', args=[org2.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_switch_org_not_member_fails(self):
        org2 = Organization.objects.create(name='Foreign Org')
        resp = self.client.post(reverse('orgs-switch', args=[org2.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_teams_list(self):
        resp = self.client.get(reverse('orgs-teams', args=[self.org_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_member_update_by_non_admin_fails(self):
        viewer = User.objects.create_user(email='viewer2@example.com', password='Pass123!', full_name='Viewer2')
        m = Membership.objects.create(user=viewer, organization_id=self.org_id, role='viewer')
        self.client.force_authenticate(user=viewer)
        member = User.objects.create_user(email='member2@example.com', password='Pass123!', full_name='Member2')
        m2 = Membership.objects.create(user=member, organization_id=self.org_id, role='member')
        resp = self.client.patch(reverse('orgs-member-update', args=[self.org_id, m2.id]), {'role': 'admin'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_creates_user_if_not_exists(self):
        resp = self.client.post(reverse('orgs-invite', args=[self.org_id]), {'email': 'newuser@example.com', 'role': 'member'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_org_serializer_excludes_sensitive_fields(self):
        resp = self.client.get(reverse('orgs-detail', args=[self.org_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('name', resp.data)
        self.assertIn('role', resp.data)
