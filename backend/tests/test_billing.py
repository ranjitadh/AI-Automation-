import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, Mock
from apps.accounts.models import User, Organization, Membership
from apps.billing.models import Plan, Subscription, Invoice, UsageEvent
from apps.accounts.views import AuthRateThrottle


class BillingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()
        self.user = User.objects.create_user(email='billing@example.com', password='Pass123!', full_name='Billing')
        self.org = Organization.objects.create(name='Billing Org')
        Membership.objects.create(user=self.user, organization=self.org, role='owner', is_default=True)
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_ORGANIZATION_ID=str(self.org.id))

    def tearDown(self):
        self._throttle_patch.stop()

    def test_plan_list_public(self):
        self.client.force_authenticate(user=None)
        self.client.credentials()
        Plan.objects.create(name='Free', slug='free', price_monthly=0, price_yearly=0, sort_order=1)
        resp = self.client.get(reverse('plans-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_subscription_get_or_create(self):
        Plan.objects.create(name='Free', slug='free', price_monthly=0, price_yearly=0, sort_order=1)
        resp = self.client.get(reverse('subscription'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_subscription_update(self):
        plan = Plan.objects.create(name='Pro', slug='pro', price_monthly=29, price_yearly=290, sort_order=2)
        Subscription.objects.create(organization=self.org, plan=plan)
        resp = self.client.patch(reverse('subscription'), {'billing_cycle': 'yearly'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_invoice_list_org_filtered(self):
        Invoice.objects.create(organization=self.org, amount=100, stripe_invoice_id='inv_org1')
        other_org = Organization.objects.create(name='Other')
        Invoice.objects.create(organization=other_org, amount=200, stripe_invoice_id='inv_other')
        resp = self.client.get(reverse('invoices-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for inv in resp.data['results']:
            self.assertEqual(str(inv['organization']), str(self.org.id))

    def test_invoice_list_owner_only(self):
        viewer = User.objects.create_user(email='viewer@example.com', password='Pass123!', full_name='Viewer')
        Membership.objects.create(user=viewer, organization=self.org, role='viewer')
        self.client.force_authenticate(user=viewer)
        resp = self.client.get(reverse('invoices-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_usage_view(self):
        Plan.objects.create(name='Free', slug='free', price_monthly=0, price_yearly=0, sort_order=1)
        UsageEvent.objects.create(organization=self.org, event_type='job_analysis', quantity=5)
        resp = self.client.get(reverse('usage'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_subscription_cancel(self):
        plan = Plan.objects.create(name='Pro', slug='pro', price_monthly=29, price_yearly=290, sort_order=2)
        Subscription.objects.create(organization=self.org, plan=plan, status='active')
        resp = self.client.post(reverse('subscription-cancel'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        sub = Subscription.objects.get(organization=self.org)
        self.assertEqual(sub.status, 'canceled')

    def test_subscription_cancel_non_owner_fails(self):
        viewer = User.objects.create_user(email='viewer@example.com', password='Pass123!', full_name='Viewer')
        Membership.objects.create(user=viewer, organization=self.org, role='viewer')
        self.client.force_authenticate(user=viewer)
        plan = Plan.objects.create(name='Pro', slug='pro', price_monthly=29, price_yearly=290, sort_order=2)
        Subscription.objects.create(organization=self.org, plan=plan, status='active')
        resp = self.client.post(reverse('subscription-cancel'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_stripe_webhook_endpoint(self):
        resp = self.client.post(reverse('stripe-webhook'), data='{}', content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
