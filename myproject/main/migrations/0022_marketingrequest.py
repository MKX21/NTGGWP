from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('main', '0021_merge_20260913_2252'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketingRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('goal', models.CharField(choices=[('exposure', '增加課程曝光'), ('enrollment', '增加招生人數'), ('new_course', '新課程宣傳'), ('promotion', '限時促銷'), ('other', '其他')], max_length=30, verbose_name='行銷目的')),
                ('desired_start_date', models.DateField(blank=True, null=True, verbose_name='希望開始日期')),
                ('notes', models.TextField(blank=True, default='', verbose_name='補充需求')),
                ('status', models.CharField(choices=[('pending', '待處理'), ('processing', '處理中'), ('completed', '已完成'), ('rejected', '已退回')], default='pending', max_length=20, verbose_name='申請狀態')),
                ('admin_note', models.TextField(blank=True, default='', verbose_name='後台備註')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='申請時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_requests', to='main.course', verbose_name='課程')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketing_requests', to=settings.AUTH_USER_MODEL, verbose_name='教師')),
            ],
            options={
                'verbose_name': 'AI 行銷申請',
                'verbose_name_plural': 'AI 行銷申請',
                'ordering': ['-created_at'],
            },
        ),
    ]
