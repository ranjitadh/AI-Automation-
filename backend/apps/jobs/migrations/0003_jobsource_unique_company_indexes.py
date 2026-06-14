from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('jobs', '0002_hnsw_index'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='jobsource',
            unique_together={('organization', 'name')},
        ),
        migrations.AlterField(
            model_name='company',
            name='industry',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='company',
            name='name',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='job',
            name='department',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='job',
            name='function',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]
