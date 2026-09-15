
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0018_withdrawalrequest_bank_info_snapshot_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="LessonMaterial",
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
                    "file",
                    models.FileField(
                        upload_to="lesson_materials/", verbose_name="檔案"
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(default=1, verbose_name="排序"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="上傳時間"),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="materials",
                        to="main.courselesson",
                        verbose_name="單元",
                    ),
                ),
            ],
            options={
                "verbose_name": "單元教材",
                "verbose_name_plural": "單元教材",
                "ordering": ["lesson", "sort_order", "id"],
            },
        ),
    ]
