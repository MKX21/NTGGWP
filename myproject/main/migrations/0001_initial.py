
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='課程名稱')),
                ('price', models.IntegerField(verbose_name='價格')),
                ('description', models.TextField(verbose_name='課程介紹')),
                ('image', models.ImageField(blank=True, null=True, upload_to='course_images/', verbose_name='課程圖片')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='講師')),
            ],
            options={
                'verbose_name': '課程',
                'verbose_name_plural': '課程管理',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', '學生'), ('teacher', '老師')], max_length=20, verbose_name='角色')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='使用者')),
            ],
            options={
                'verbose_name': '使用者資料',
                'verbose_name_plural': '使用者資料',
            },
        ),
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchased_at', models.DateTimeField(auto_now_add=True, verbose_name='購買時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.course', verbose_name='課程')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='學生')),
            ],
            options={
                'verbose_name': '購課紀錄',
                'verbose_name_plural': '購課紀錄',
                'unique_together': {('student', 'course')},
            },
        ),
    ]
