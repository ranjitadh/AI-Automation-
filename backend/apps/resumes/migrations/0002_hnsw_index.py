from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS resumes_resume_embedding_idx ON resumes_resume USING hnsw (embedding vector_cosine_ops)",
            "DROP INDEX IF EXISTS resumes_resume_embedding_idx",
        ),
    ]
