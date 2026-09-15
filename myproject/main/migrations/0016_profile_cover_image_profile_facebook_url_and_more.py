
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0015_withdrawalrequest_revenuerecord_coursesplitsetting"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="cover_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="teacher_covers/",
                verbose_name="講師頁封面",
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="facebook_url",
            field=models.URLField(blank=True, default="", verbose_name="Facebook 連結"),
        ),
        migrations.AddField(
            model_name="profile",
            name="headline",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="講師稱號"
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="youtube_url",
            field=models.URLField(blank=True, default="", verbose_name="YouTube 連結"),
        ),
        migrations.CreateModel(
            name="TeacherColumn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="專欄名稱")),
                (
                    "description",
                    models.TextField(blank=True, default="", verbose_name="專欄簡介"),
                ),
                (
                    "cover_image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="teacher_columns/",
                        verbose_name="專欄封面",
                    ),
                ),
                (
                    "is_published",
                    models.BooleanField(default=True, verbose_name="是否公開"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="建立時間"),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="columns",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="講師",
                    ),
                ),
            ],
            options={
                "verbose_name": "專欄",
                "verbose_name_plural": "專欄",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TeacherArticle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="文章標題")),
                ("content", models.TextField(verbose_name="文章內容")),
                (
                    "cover_image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="teacher_articles/",
                        verbose_name="文章封面",
                    ),
                ),
                (
                    "is_published",
                    models.BooleanField(default=True, verbose_name="是否公開"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="建立時間"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="articles",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="講師",
                    ),
                ),
                (
                    "column",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="articles",
                        to="main.teachercolumn",
                        verbose_name="所屬專欄",
                    ),
                ),
            ],
            options={
                "verbose_name": "文章",
                "verbose_name_plural": "文章",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TeacherMaterial",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="教材名稱")),
                (
                    "description",
                    models.TextField(blank=True, default="", verbose_name="教材說明"),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to="teacher_materials/", verbose_name="教材檔案"
                    ),
                ),
                (
                    "is_published",
                    models.BooleanField(default=True, verbose_name="是否公開"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="建立時間"),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materials",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="講師",
                    ),
                ),
            ],
            options={
                "verbose_name": "教材",
                "verbose_name_plural": "教材",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TeacherFollow",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="追蹤時間"),
                ),
                (
                    "follower",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="following",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="追蹤者",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="followers",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="講師",
                    ),
                ),
            ],
            options={
                "verbose_name": "追蹤講師",
                "verbose_name_plural": "追蹤講師",
                "ordering": ["-created_at"],
                "unique_together": {("follower", "teacher")},
            },
        ),
    ]
