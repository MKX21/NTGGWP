
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_withdrawalrequest_bank_info_snapshot_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseanswer',
            name='is_ai_generated',
            field=models.BooleanField(default=False, verbose_name='AI 自動回答'),
        ),
    ]
