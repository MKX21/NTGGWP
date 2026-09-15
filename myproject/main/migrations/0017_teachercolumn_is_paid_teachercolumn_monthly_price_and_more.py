
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0016_profile_cover_image_profile_facebook_url_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="teachercolumn",
            name="is_paid",
            field=models.BooleanField(default=False, verbose_name="付費訂閱專欄"),
        ),
        migrations.AddField(
            model_name="teachercolumn",
            name="monthly_price",
            field=models.PositiveIntegerField(default=0, verbose_name="月費（NT$）"),
        ),
        migrations.CreateModel(
            name="ColumnSubscription",
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
                    "started_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="訂閱開始"),
                ),
                ("expires_at", models.DateTimeField(verbose_name="到期時間")),
                (
                    "column",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to="main.teachercolumn",
                        verbose_name="專欄",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="column_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="訂閱者",
                    ),
                ),
            ],
            options={
                "verbose_name": "專欄訂閱",
                "verbose_name_plural": "專欄訂閱",
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="UserBadge",
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
                ("code", models.CharField(max_length=50, verbose_name="徽章代碼")),
                (
                    "earned_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="獲得時間"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="badges",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="使用者",
                    ),
                ),
            ],
            options={
                "verbose_name": "成就徽章",
                "verbose_name_plural": "成就徽章",
                "ordering": ["-earned_at"],
                "unique_together": {("user", "code")},
            },
        ),
    ]
