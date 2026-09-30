"""把課程教材抽取文字、切塊、灌進 Azure AI Search。

用法：
  python manage.py build_search_index            # 索引所有課程
  python manage.py build_search_index --course 33  # 只索引指定課程
"""
from django.core.management.base import BaseCommand, CommandError

from main import rag
from main.models import Course


class Command(BaseCommand):
    help = '抽取課程教材文字並建立 Azure AI Search 索引（RAG 用）'

    def add_arguments(self, parser):
        parser.add_argument('--course', type=int, default=None,
                            help='只索引指定課程 ID；不給則索引所有課程')

    def handle(self, *args, **options):
        if not rag.is_search_enabled():
            raise CommandError('Azure AI Search 尚未設定（請檢查 .env 的 AZURE_SEARCH_*）。')

        course_id = options['course']
        if course_id:
            courses = Course.objects.filter(id=course_id)
            if not courses:
                raise CommandError(f'找不到課程 ID {course_id}。')
        else:
            courses = Course.objects.all()

        self.stdout.write('建立 / 確認索引…')
        rag.ensure_index()

        grand = {'materials_indexed': 0, 'chunks': 0, 'skipped': 0}
        for course in courses:
            self.stdout.write(f'\n索引課程：{course.title}（ID {course.id}）')
            stats = rag.index_course(course, stdout=self.stdout.write)
            for k in grand:
                grand[k] += stats[k]
            self.stdout.write(self.style.SUCCESS(
                f"  完成：{stats['materials_indexed']} 個教材、"
                f"{stats['chunks']} 個片段（略過 {stats['skipped']} 個無法抽取）"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\n全部完成：共索引 {grand['materials_indexed']} 個教材、"
            f"{grand['chunks']} 個片段。"
        ))
