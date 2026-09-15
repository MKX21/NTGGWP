
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_marketingrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketingPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_audience', models.TextField(blank=True, default='', verbose_name='目標受眾')),
                ('course_selling_points', models.TextField(blank=True, default='', verbose_name='課程賣點')),
                ('marketing_strategy', models.TextField(blank=True, default='', verbose_name='行銷策略')),
                ('ad_headline', models.TextField(blank=True, default='', verbose_name='廣告標題')),
                ('ad_copy', models.TextField(blank=True, default='', verbose_name='廣告文案')),
                ('social_media_copy', models.TextField(blank=True, default='', verbose_name='社群貼文')),
                ('video_script', models.TextField(blank=True, default='', verbose_name='短影音腳本')),
                ('call_to_action', models.CharField(blank=True, default='', max_length=255, verbose_name='行動呼籲')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('reviewing', '待審核'), ('approved', '已核准'), ('rejected', '已退回')], default='draft', max_length=20, verbose_name='企劃狀態')),
                ('admin_note', models.TextField(blank=True, default='', verbose_name='管理員備註')),
                ('generated_at', models.DateTimeField(blank=True, null=True, verbose_name='AI 生成時間')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='審核時間')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('marketing_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='plan', to='main.marketingrequest', verbose_name='行銷申請')),
            ],
            options={
                'verbose_name': 'AI 行銷企劃',
                'verbose_name_plural': 'AI 行銷企劃',
                'ordering': ['-created_at'],
            },
        ),
    ]
