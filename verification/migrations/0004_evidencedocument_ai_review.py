import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('verification', '0003_evidencedocument_screened_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='evidencedocument',
            name='confidence_score',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddField(
            model_name='evidencedocument',
            name='ai_recommendation',
            field=models.CharField(
                choices=[
                    ('APPROVED', 'Recommend approval'),
                    ('REJECTED', 'Recommend rejection'),
                    ('REQUIRES_REVIEW', 'Requires manual review'),
                ],
                default='REQUIRES_REVIEW',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='evidencedocument',
            name='audit_reasons',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
