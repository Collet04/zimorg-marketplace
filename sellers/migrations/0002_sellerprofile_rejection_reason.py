from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sellers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerprofile',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
    ]
