from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('campaigns', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='campaign',
            unique_together={('organization', 'name')},
        ),
    ]
