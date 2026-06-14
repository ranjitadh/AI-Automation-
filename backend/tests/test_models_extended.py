import pytest
from django.test import TestCase
from django.db import connection, models
from django.apps import apps


class ModelConstraintTests(TestCase):
    def test_campaign_unique_org_name(self):
        from apps.campaigns.models import Campaign
        constraints = Campaign._meta.unique_together
        self.assertIn(('organization', 'name'), constraints)

    def test_job_source_unique_org_name(self):
        from apps.jobs.models import JobSource
        constraints = JobSource._meta.unique_together
        self.assertIn(('organization', 'name'), constraints)

    def test_invoice_stripe_id_unique(self):
        from apps.billing.models import Invoice
        field = Invoice._meta.get_field('stripe_invoice_id')
        self.assertTrue(field.unique)

    def test_company_name_indexed(self):
        from apps.jobs.models import Company
        field = Company._meta.get_field('name')
        self.assertTrue(field.db_index)

    def test_job_department_indexed(self):
        from apps.jobs.models import Job
        field = Job._meta.get_field('department')
        self.assertTrue(field.db_index)

    def test_job_function_indexed(self):
        from apps.jobs.models import Job
        field = Job._meta.get_field('function')
        self.assertTrue(field.db_index)

    def test_company_industry_indexed(self):
        from apps.jobs.models import Company
        field = Company._meta.get_field('industry')
        self.assertTrue(field.db_index)

    def test_pipeline_run_has_organization(self):
        from apps.pipeline.models import PipelineRun
        field = PipelineRun._meta.get_field('organization')
        self.assertIsNotNone(field)
        self.assertIsInstance(field, models.ForeignKey)

    def test_all_models_have_id_field(self):
        model_apps = ['accounts', 'resumes', 'jobs', 'analysis', 'campaigns',
                       'applications', 'cover_letters', 'questions', 'interviews',
                       'recruiters', 'automation', 'billing', 'notifications', 'audit',
                       'pipeline', 'common']
        for app_label in model_apps:
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                continue
            for model in app_config.get_models():
                with self.subTest(model=model.__name__):
                    self.assertTrue(hasattr(model, 'id') or any(f.primary_key for f in model._meta.get_fields()),
                                    f"{model.__name__} has no primary key")

    def test_string_representation(self):
        from apps.jobs.models import Company
        c = Company(name='TestCorp')
        self.assertEqual(str(c), 'TestCorp')

    def test_org_settings_default_resume_nullable(self):
        from apps.common.models import OrganizationSettings
        field = OrganizationSettings._meta.get_field('default_resume')
        self.assertTrue(field.null)


class SerializerFieldTests(TestCase):
    def test_no_serializer_uses_fields_all(self):
        import os
        import re
        apps_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'apps')
        all_ok = True
        for root, dirs, files in os.walk(apps_dir):
            for f in files:
                if f.endswith('.py'):
                    filepath = os.path.join(root, f)
                    with open(filepath) as fh:
                        content = fh.read()
                        if "fields = '__all__'" in content or 'fields = "__all__"' in content:
                            all_ok = False
                            self.fail(f"Found fields='__all__' in {filepath}")
        self.assertTrue(all_ok, "All serializers should use explicit fields")
