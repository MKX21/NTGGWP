
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0023_marketingplan"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VMAccessRequest",
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
                    "reason",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="例如：課程需要的軟體只有 Windows 版本，Mac 無法安裝。",
                        verbose_name="申請原因",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "待審核"),
                            ("approved", "已核發"),
                            ("rejected", "已拒絕"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="申請狀態",
                    ),
                ),
                (
                    "vm_url",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="虛擬機網址",
                    ),
                ),
                (
                    "vm_username",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="虛擬機帳號",
                    ),
                ),
                (
                    "vm_password",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="虛擬機密碼",
                    ),
                ),
                (
                    "admin_note",
                    models.TextField(blank=True, default="", verbose_name="後台備註"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="申請時間"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="核發時間"
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vm_access_requests",
                        to="main.course",
                        verbose_name="購買課程",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vm_access_requests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="申請學生",
                    ),
                ),
            ],
            options={
                "verbose_name": "Mac 虛擬機申請",
                "verbose_name_plural": "Mac 虛擬機申請",
                "ordering": ["-created_at"],
            },
        ),
    ]
