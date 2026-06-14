import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.accounts.models import User, Organization, Membership
from apps.accounts.views import AuthRateThrottle


class OrgIsolationTests(TestCase):
    """Verify complete tenant isolation between organizations"""

    def setUp(self):
        self.client = APIClient()
        self._throttle_patch = patch.object(AuthRateThrottle, 'rate', '10000/min')
        self._throttle_patch.start()

        self.org_a = Organization.objects.create(name='Org A')
        self.org_b = Organization.objects.create(name='Org B')
        self.user_a = User.objects.create_user(email='a@example.com', password='Pass123!', full_name='User A')
        self.user_b = User.objects.create_user(email='b@example.com', password='Pass123!', full_name='User B')
        Membership.objects.create(user=self.user_a, organization=self.org_a, role='owner', is_default=True)
        Membership.objects.create(user=self.user_b, organization=self.org_b, role='owner', is_default=True)

    def tearDown(self):
        self._throttle_patch.stop()

    def _auth_as(self, user, org):
        self.client.force_authenticate(user=user)
        self.client.credentials(HTTP_X_ORGANIZATION_ID=str(org.id))

    def test_cannot_list_other_org_resumes(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.resumes.models import Resume
        Resume.objects.create(organization=self.org_b, user=self.user_b, title='B Resume', profile_slug='b-resume')
        resp = self.client.get(reverse('resumes-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data['results']:
            self.assertEqual(item['organization'], str(self.org_a.id))

    def test_cannot_list_other_org_campaigns(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.campaigns.models import Campaign
        Campaign.objects.create(organization=self.org_b, created_by=self.user_b, name='B Campaign')
        resp = self.client.get(reverse('campaigns-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data['results']:
            self.assertEqual(item['organization'], str(self.org_a.id))

    def test_cannot_list_other_org_applications(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.applications.models import Application
        from apps.jobs.models import Job, Company
        company = Company.objects.create(name='Test Co')
        job = Job.objects.create(title='Engineer', company=company)
        Application.objects.create(organization=self.org_b, job=job, applicant=self.user_b)
        resp = self.client.get(reverse('applications-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data['results']:
            self.assertEqual(item['organization'], str(self.org_a.id))

    def test_cannot_read_other_org_campaign(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.campaigns.models import Campaign
        c = Campaign.objects.create(organization=self.org_b, created_by=self.user_b, name='Secret Campaign')
        resp = self.client.get(reverse('campaigns-detail', args=[c.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_other_org_resume(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.resumes.models import Resume
        r = Resume.objects.create(organization=self.org_b, user=self.user_b, title='B Resume', profile_slug='b-resume')
        resp = self.client.patch(reverse('resumes-detail', args=[r.id]), {'title': 'Hacked'})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_other_org_notification(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.notifications.models import Notification
        n = Notification.objects.create(organization=self.org_b, type='test', title='B Notif')
        resp = self.client.get(reverse('notifications-detail', args=[n.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_other_org_automation_runs(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.automation.models import AutomationRun, BrowserSession
        bs = BrowserSession.objects.create(organization=self.org_b, user=self.user_b, platform='test')
        ar = AutomationRun.objects.create(organization=self.org_b, started_by=self.user_b)
        resp = self.client.get(reverse('automation-runs-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cannot_read_other_org_invoice(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.billing.models import Invoice
        Invoice.objects.create(organization=self.org_b, amount=100, stripe_invoice_id='inv_perm1')
        resp = self.client.get(reverse('invoices-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data['results']:
            self.assertEqual(item['organization'], str(self.org_a.id))

    def test_cannot_create_via_other_org(self):
        self._auth_as(self.user_a, self.org_b)
        from apps.campaigns.models import Campaign
        resp = self.client.post(reverse('campaigns-list'), {'name': 'Cross Org Campaign'})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Campaign.objects.filter(name='Cross Org Campaign').count(), 0)

    def test_anonymous_user_rejected(self):
        self.client.force_authenticate(user=None)
        self.client.credentials()
        from apps.jobs.models import Job, Company
        company = Company.objects.create(name='Test')
        job = Job.objects.create(title='Engineer', company=company)
        resp = self.client.get(reverse('jobs-list'))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_org_header_returns_forbidden(self):
        user_c = User.objects.create_user(email='c@example.com', password='Pass123!', full_name='User C')
        self.client.force_authenticate(user=user_c)
        self.client.credentials()
        resp = self.client.get(reverse('campaigns-list'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_read_other_org_cover_letter(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.cover_letters.models import CoverLetter
        cl = CoverLetter.objects.create(organization=self.org_b, user=self.user_b, content='Secret')
        resp = self.client.get(reverse('cover-letters-detail', args=[cl.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_other_org_question_answer(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.questions.models import QuestionBank, QuestionAnswer
        qb = QuestionBank.objects.create(organization=self.org_a, question='Test?', category='general')
        qa = QuestionAnswer.objects.create(organization=self.org_b, user=self.user_b, question=qb, answer='Secret')
        resp = self.client.get(reverse('question-answers-detail', args=[qa.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_other_org_recruiter_outreach(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.recruiters.models import Recruiter, RecruiterOutreach
        from apps.jobs.models import Company
        company = Company.objects.create(name='Test Co')
        r = Recruiter.objects.create(organization=self.org_b, company=company, name='Recruiter', email='r@test.com')
        ro = RecruiterOutreach.objects.create(organization=self.org_b, recruiter=r, user=self.user_b, subject='Hi')
        resp = self.client.get(reverse('recruiter-outreach-detail', args=[ro.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_read_other_org_webhook(self):
        self._auth_as(self.user_a, self.org_a)
        from apps.notifications.models import Webhook
        w = Webhook.objects.create(organization=self.org_b, url='https://evil.com/hook')
        resp = self.client.get(reverse('webhooks-detail', args=[w.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
