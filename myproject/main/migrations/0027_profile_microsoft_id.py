from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0026_coursecertificate'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='microsoft_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True, verbose_name='Microsoft 帳號 ID'),
        ),
    ]
