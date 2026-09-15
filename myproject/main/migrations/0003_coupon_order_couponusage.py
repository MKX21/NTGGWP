
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_learningrecord'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='優惠碼')),
                ('name', models.CharField(max_length=100, verbose_name='優惠券名稱')),
                ('discount_type', models.CharField(choices=[('amount', '固定金額折扣'), ('percent', '百分比折扣')], max_length=20, verbose_name='折扣類型')),
                ('discount_value', models.PositiveIntegerField(verbose_name='折扣數值')),
                ('min_spend', models.PositiveIntegerField(default=0, verbose_name='最低消費金額')),
                ('start_date', models.DateTimeField(verbose_name='開始時間')),
                ('end_date', models.DateTimeField(verbose_name='結束時間')),
                ('usage_limit', models.PositiveIntegerField(default=0, verbose_name='總使用次數限制，0代表不限')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否啟用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
            ],
            options={
                'verbose_name': '優惠券',
                'verbose_name_plural': '優惠券管理',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_price', models.PositiveIntegerField(verbose_name='原價')),
                ('discount_amount', models.PositiveIntegerField(default=0, verbose_name='折扣金額')),
                ('final_price', models.PositiveIntegerField(verbose_name='實付金額')),
                ('status', models.CharField(choices=[('paid', '已付款'), ('cancelled', '已取消')], default='paid', max_length=20, verbose_name='訂單狀態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('coupon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.coupon', verbose_name='使用優惠券')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='購買者')),
            ],
            options={
                'verbose_name': '訂單',
                'verbose_name_plural': '訂單管理',
            },
        ),
        migrations.CreateModel(
            name='CouponUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_amount', models.PositiveIntegerField(verbose_name='實際折扣金額')),
                ('used_at', models.DateTimeField(auto_now_add=True, verbose_name='使用時間')),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='main.coupon', verbose_name='優惠券')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='main.order', verbose_name='訂單')),
            ],
            options={
                'verbose_name': '優惠券使用紀錄',
                'verbose_name_plural': '優惠券使用紀錄',
            },
        ),
    ]
