from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS jobs_job_embedding_idx ON jobs_job USING hnsw (embedding vector_cosine_ops)",
            "DROP INDEX IF EXISTS jobs_job_embedding_idx",
        ),
    ]
