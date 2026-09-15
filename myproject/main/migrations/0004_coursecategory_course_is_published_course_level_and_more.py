
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_coupon_order_couponusage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='分類名稱')),
                ('description', models.TextField(blank=True, null=True, verbose_name='分類說明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
            ],
            options={
                'verbose_name': '課程分類',
                'verbose_name_plural': '課程分類',
            },
        ),
        migrations.AddField(
            model_name='course',
            name='is_published',
            field=models.BooleanField(default=True, verbose_name='是否上架'),
        ),
        migrations.AddField(
            model_name='course',
            name='level',
            field=models.CharField(choices=[('beginner', '初階'), ('intermediate', '中階'), ('advanced', '高階')], default='beginner', max_length=20, verbose_name='課程難度'),
        ),
        migrations.AlterField(
            model_name='order',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', '待付款'), ('paid', '已付款'), ('cancelled', '已取消'), ('refunded', '已退款')], default='paid', max_length=20, verbose_name='訂單狀態'),
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '購物車',
                'verbose_name_plural': '購物車',
            },
        ),
        migrations.CreateModel(
            name='CourseAudit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '待審核'), ('approved', '審核通過'), ('rejected', '審核退回')], default='pending', max_length=20, verbose_name='審核狀態')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='審核意見')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='送審時間')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='審核時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('reviewer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='審核人員')),
            ],
            options={
                'verbose_name': '課程審核',
                'verbose_name_plural': '課程審核',
            },
        ),
        migrations.AddField(
            model_name='course',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.coursecategory', verbose_name='課程分類'),
        ),
        migrations.CreateModel(
            name='CourseChapter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='章節名稱')),
                ('description', models.TextField(blank=True, null=True, verbose_name='章節說明')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='章節順序')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chapters', to='main.course', verbose_name='課程')),
            ],
            options={
                'verbose_name': '課程章節',
                'verbose_name_plural': '課程章節',
                'ordering': ['course', 'sort_order'],
            },
        ),
        migrations.CreateModel(
            name='CourseLesson',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='單元名稱')),
                ('content', models.TextField(blank=True, null=True, verbose_name='單元內容')),
                ('video_url', models.URLField(blank=True, null=True, verbose_name='影片連結')),
                ('duration_minutes', models.PositiveIntegerField(default=0, verbose_name='影片分鐘數')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='單元順序')),
                ('is_free_preview', models.BooleanField(default=False, verbose_name='是否免費試看')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('chapter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lessons', to='main.coursechapter', verbose_name='章節')),
            ],
            options={
                'verbose_name': '課程單元',
                'verbose_name_plural': '課程單元',
                'ordering': ['chapter', 'sort_order'],
            },
        ),
        migrations.AddField(
            model_name='learningrecord',
            name='lesson',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.courselesson', verbose_name='觀看單元'),
        ),
        migrations.CreateModel(
            name='CourseQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='問題標題')),
                ('content', models.TextField(verbose_name='問題內容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='提問時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.courselesson', verbose_name='相關單元')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='提問者')),
            ],
            options={
                'verbose_name': '課程問答',
                'verbose_name_plural': '課程問答',
            },
        ),
        migrations.CreateModel(
            name='CourseAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='回答內容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='回答時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='回答者')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='main.coursequestion', verbose_name='問題')),
            ],
            options={
                'verbose_name': '課程回答',
                'verbose_name_plural': '課程回答',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='通知標題')),
                ('content', models.TextField(verbose_name='通知內容')),
                ('is_read', models.BooleanField(default=False, verbose_name='是否已讀')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='接收者')),
            ],
            options={
                'verbose_name': '通知',
                'verbose_name_plural': '通知',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.PositiveIntegerField(verbose_name='購買當下價格')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='main.order', verbose_name='訂單')),
            ],
            options={
                'verbose_name': '訂單明細',
                'verbose_name_plural': '訂單明細',
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('credit_card', '信用卡'), ('atm', 'ATM轉帳'), ('line_pay', 'LINE Pay'), ('cash', '現金'), ('mock', '模擬付款')], default='mock', max_length=30, verbose_name='付款方式')),
                ('amount', models.PositiveIntegerField(verbose_name='付款金額')),
                ('status', models.CharField(choices=[('pending', '待付款'), ('paid', '付款成功'), ('failed', '付款失敗'), ('refunded', '已退款')], default='paid', max_length=20, verbose_name='付款狀態')),
                ('transaction_no', models.CharField(blank=True, max_length=100, null=True, verbose_name='交易編號')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='付款時間')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='main.order', verbose_name='訂單')),
            ],
            options={
                'verbose_name': '付款紀錄',
                'verbose_name_plural': '付款紀錄',
            },
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='促銷活動名稱')),
                ('description', models.TextField(blank=True, null=True, verbose_name='活動說明')),
                ('discount_type', models.CharField(choices=[('amount', '固定金額折扣'), ('percent', '百分比折扣')], max_length=20, verbose_name='折扣類型')),
                ('discount_value', models.PositiveIntegerField(verbose_name='折扣數值')),
                ('start_date', models.DateTimeField(verbose_name='開始時間')),
                ('end_date', models.DateTimeField(verbose_name='結束時間')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否啟用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('courses', models.ManyToManyField(blank=True, to='main.course', verbose_name='適用課程')),
            ],
            options={
                'verbose_name': '促銷活動',
                'verbose_name_plural': '促銷活動',
            },
        ),
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField(verbose_name='退款金額')),
                ('reason', models.TextField(verbose_name='退款原因')),
                ('status', models.CharField(choices=[('pending', '退款審核中'), ('approved', '退款通過'), ('rejected', '退款拒絕'), ('completed', '退款完成')], default='pending', max_length=20, verbose_name='退款狀態')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='申請時間')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='處理時間')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refunds', to='main.order', verbose_name='訂單')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='申請者')),
            ],
            options={
                'verbose_name': '退款紀錄',
                'verbose_name_plural': '退款紀錄',
            },
        ),
        migrations.CreateModel(
            name='UserCoupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('unused', '未使用'), ('used', '已使用'), ('expired', '已過期')], default='unused', max_length=20, verbose_name='使用狀態')),
                ('received_at', models.DateTimeField(auto_now_add=True, verbose_name='領取時間')),
                ('used_at', models.DateTimeField(blank=True, null=True, verbose_name='使用時間')),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.coupon', verbose_name='優惠券')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '使用者優惠券',
                'verbose_name_plural': '使用者優惠券',
            },
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='加入時間')),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='main.cart', verbose_name='購物車')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
            ],
            options={
                'verbose_name': '購物車明細',
                'verbose_name_plural': '購物車明細',
                'unique_together': {('cart', 'course')},
            },
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='收藏時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '收藏課程',
                'verbose_name_plural': '收藏課程',
                'unique_together': {('user', 'course')},
            },
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(default=5, verbose_name='評分')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='評論內容')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='評論時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='評論者')),
            ],
            options={
                'verbose_name': '課程評價',
                'verbose_name_plural': '課程評價',
                'unique_together': {('user', 'course')},
            },
        ),
    ]
