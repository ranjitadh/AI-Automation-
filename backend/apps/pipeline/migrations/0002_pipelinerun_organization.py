from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('pipeline', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipelinerun',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pipeline_runs', to='accounts.organization', db_index=True),
            preserve_default=False,
        ),
    ]
