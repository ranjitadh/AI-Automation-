# Generated manually for Career Agent engines

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0001_initial'),
        ('accounts', '0001_initial'),
        ('jobs', '0001_initial'),
        ('applications', '0001_initial'),
        ('resumes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationDecision',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('decision', models.CharField(choices=[('apply', 'Apply'), ('reject', 'Reject'), ('review', 'Review'), ('queue', 'Queue')], db_index=True, max_length=20)),
                ('fit_score', models.IntegerField(default=0)),
                ('skill_match_score', models.IntegerField(default=0)),
                ('experience_match_score', models.IntegerField(default=0)),
                ('seniority_match_score', models.IntegerField(default=0)),
                ('industry_match_score', models.IntegerField(default=0)),
                ('salary_match_score', models.IntegerField(default=0)),
                ('location_match_score', models.IntegerField(default=0)),
                ('overqualification_risk', models.CharField(default='none', max_length=20)),
                ('underqualification_risk', models.CharField(default='none', max_length=20)),
                ('auto_reject_reason', models.TextField(blank=True)),
                ('reasoning', models.TextField(blank=True)),
                ('confidence', models.FloatField(default=0.0)),
                ('threshold_used', models.IntegerField(default=70)),
                ('auto_apply', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='application_decisions', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='application_decisions', to='accounts.organization')),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='decisions', to='jobs.job')),
            ],
            options={
                'db_table': 'application_decisions',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'job')},
            },
        ),
        migrations.CreateModel(
            name='ApplicationOutcome',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('outcome', models.CharField(choices=[('no_response', 'No Response'), ('rejected', 'Rejected'), ('screen', 'Screen'), ('interview', 'Interview'), ('offer', 'Offer'), ('accepted', 'Accepted'), ('withdrawn', 'Withdrawn')], db_index=True, default='no_response', max_length=20)),
                ('response_time_days', models.IntegerField(blank=True, null=True)),
                ('interview_rounds', models.IntegerField(blank=True, null=True)),
                ('offer_amount', models.IntegerField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('feedback', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('cover_letter_version', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outcomes', to='applications.application')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='application_outcomes', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='application_outcomes', to='accounts.organization')),
                ('resume_version_used', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='resumes.resumeversion')),
            ],
            options={
                'db_table': 'application_outcomes',
                'ordering': ['-created_at'],
            },
        ),
    ]
