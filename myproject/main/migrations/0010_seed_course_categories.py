from django.db import migrations

# 教師建課時只能從這 12 種固定分類挑選，不再開放自訂新分類。
CURATED_CATEGORIES = [
    '程式設計', '設計美學', '行銷與業務', '商業管理', '攝影剪輯',
    '影視製作', '音樂', '語言學習', '個人成長', '手作生活',
    '職場技能', '學術教育',
]


def seed_categories(apps, schema_editor):
    CourseCategory = apps.get_model('main', 'CourseCategory')
    Course = apps.get_model('main', 'Course')

    # 既有「設計與行銷」併入新名稱「設計美學」，保留底下課程的分類關聯
    old = CourseCategory.objects.filter(name='設計與行銷').first()
    if old:
        target = CourseCategory.objects.filter(name='設計美學').exclude(pk=old.pk).first()
        if target:
            Course.objects.filter(category=old).update(category=target)
            old.delete()
        else:
            old.name = '設計美學'
            old.save(update_fields=['name'])

    for name in CURATED_CATEGORIES:
        CourseCategory.objects.get_or_create(name=name)

    # 不在固定名單內的分類（含測試期間留下的雜項）底下課程轉入「程式設計」，再移除該分類
    fallback = CourseCategory.objects.get(name='程式設計')
    for cat in CourseCategory.objects.exclude(name__in=CURATED_CATEGORIES):
        Course.objects.filter(category=cat).update(category=fallback)
        cat.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_course_discount_price_course_early_bird_price_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop),
    ]
