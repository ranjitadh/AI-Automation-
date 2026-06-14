from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='stripe_invoice_id',
            field=models.CharField(blank=True, max_length=255, unique=True),
        ),
    ]
