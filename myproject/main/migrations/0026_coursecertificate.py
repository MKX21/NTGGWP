import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_fix_order_payment_default_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseCertificate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('certificate_number', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='證書編號')),
                ('issued_at', models.DateTimeField(auto_now_add=True, verbose_name='核發時間')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='main.course', verbose_name='課程')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_certificates', to=settings.AUTH_USER_MODEL, verbose_name='學生')),
            ],
            options={
                'verbose_name': '課程結業證書',
                'verbose_name_plural': '課程結業證書',
                'ordering': ('-issued_at',),
                'constraints': [models.UniqueConstraint(fields=('student', 'course'), name='unique_student_course_certificate')],
            },
        ),
    ]
