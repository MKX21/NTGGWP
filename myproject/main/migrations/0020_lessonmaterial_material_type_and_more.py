
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0019_lessonmaterial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lessonmaterial",
            name="material_type",
            field=models.CharField(
                choices=[
                    ("slides", "簡報"),
                    ("practice", "練習檔"),
                    ("reading", "延伸閱讀"),
                    ("other", "其他"),
                ],
                default="slides",
                max_length=20,
                verbose_name="教材類型",
            ),
        ),
        migrations.AddField(
            model_name="lessonmaterial",
            name="size_bytes",
            field=models.PositiveBigIntegerField(
                default=0, verbose_name="檔案大小(bytes)"
            ),
        ),
    ]
