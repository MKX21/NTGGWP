from django.db import migrations


def backfill_is_teacher(apps, schema_editor):
    Profile = apps.get_model('main', 'Profile')
    Profile.objects.filter(role='teacher').update(is_teacher=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_course_promo_video_type_course_teacher_revenue_share_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_is_teacher, noop_reverse),
    ]
