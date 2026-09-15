
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_course_access_duration_days_course_intro_video_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='discount_amount',
            field=models.PositiveIntegerField(default=0, verbose_name='此項折扣金額'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='paid_amount',
            field=models.PositiveIntegerField(default=0, verbose_name='此項實付金額'),
        ),
    ]
