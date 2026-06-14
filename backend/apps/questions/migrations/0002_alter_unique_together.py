from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('questions', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='questionbank',
            unique_together={('organization', 'question')},
        ),
    ]
