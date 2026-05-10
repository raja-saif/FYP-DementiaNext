# Generated manually for subtype classifier support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detection', '0003_alter_detectionresult_predicted_class'),
    ]

    operations = [
        migrations.AddField(
            model_name='detectionresult',
            name='model_type',
            field=models.CharField(
                choices=[
                    ('binary', 'Binary Dementia Detector'),
                    ('subtype', 'Subtype Classifier'),
                ],
                default='binary',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='detectionresult',
            name='predicted_class',
            field=models.CharField(
                blank=True,
                choices=[
                    ('alzheimers', "Alzheimer's Disease"),
                    ('cn', 'Control/Normal'),
                    ('pd', "Parkinson's Disease"),
                    ('ftd', 'Frontotemporal Dementia'),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
