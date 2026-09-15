
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minutes', models.PositiveIntegerField(default=30, verbose_name='觀看分鐘數')),
                ('watched_at', models.DateTimeField(auto_now_add=True, verbose_name='觀看時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '學習紀錄',
                'verbose_name_plural': '學習紀錄',
            },
        ),
    ]
