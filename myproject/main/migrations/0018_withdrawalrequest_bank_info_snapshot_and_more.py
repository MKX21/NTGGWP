
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0017_teachercolumn_is_paid_teachercolumn_monthly_price_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="withdrawalrequest",
            name="bank_info_snapshot",
            field=models.TextField(blank=True, default="", verbose_name="銀行帳戶快照"),
        ),
        migrations.CreateModel(
            name="TeacherBankAccount",
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
                    "bank_name",
                    models.CharField(max_length=100, verbose_name="銀行名稱"),
                ),
                (
                    "bank_code",
                    models.CharField(
                        blank=True, max_length=10, null=True, verbose_name="銀行代碼"
                    ),
                ),
                (
                    "branch_name",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="分行名稱"
                    ),
                ),
                ("account_name", models.CharField(max_length=100, verbose_name="戶名")),
                (
                    "account_number",
                    models.CharField(max_length=50, verbose_name="帳號"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
                (
                    "teacher",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bank_account",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="教師",
                    ),
                ),
            ],
            options={
                "verbose_name": "教師銀行帳戶",
                "verbose_name_plural": "教師銀行帳戶",
            },
        ),
    ]
