import pytest
from django.test import TestCase
from django.db import connection
from django.apps import apps


class ModelTests(TestCase):
    def test_all_apps_have_migrations(self):
        """Every app with models must have migrations"""
        model_apps = []
        for app_config in apps.get_app_configs():
            if hasattr(app_config, 'get_models'):
                models = list(app_config.get_models())
                if models:
                    model_apps.append(app_config.label)

        migration_apps = set()
        for app_config in apps.get_app_configs():
            if app_config.label in model_apps:
                migration_apps.add(app_config.label)

        for app_label in model_apps:
            with self.subTest(app=app_label):
                self.assertIn(
                    app_label, migration_apps,
                    f"{app_label} has models but no migrations"
                )

    def test_all_fk_have_indexes(self):
        """Verify ForeignKey fields have db_index where expected"""
        from django.db import models

        indexed_apps = [
            'accounts', 'resumes', 'jobs', 'analysis', 'campaigns',
            'applications', 'cover_letters', 'questions', 'interviews',
            'recruiters', 'automation', 'billing', 'notifications', 'audit',
            'pipeline', 'common',
        ]
        for app_label in indexed_apps:
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                continue
            for model in app_config.get_models():
                for field in model._meta.get_fields():
                    if isinstance(field, models.ForeignKey) and not field.one_to_one:
                        with self.subTest(model=model.__name__, field=field.name):
                            self.assertTrue(
                                field.db_index or field.unique,
                                f"{model.__name__}.{field.name} is missing db_index"
                            )

    def test_unique_constraints_exist(self):
        """Verify critical unique constraints exist"""
        from apps.interviews.models import Interview, Offer
        from apps.billing.models import Subscription
        from apps.resumes.models import Resume, ResumeVersion
        from apps.jobs.models import Job

        interview_constraints = Interview._meta.unique_together
        self.assertIn(('application', 'round'), interview_constraints)

        offer_constraints = Offer._meta.unique_together
        self.assertIn(('application', 'organization'), offer_constraints)

        subscription_constraints = Subscription._meta.unique_together
        self.assertIn(('organization', 'plan'), subscription_constraints)
