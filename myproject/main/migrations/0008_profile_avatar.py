
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_lessonprogress'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='大頭貼'),
        ),
    ]
