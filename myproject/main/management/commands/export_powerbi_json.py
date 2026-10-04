"""把 LearnMate 的真實學習資料匯出成 Power BI 用的 JSON。

產出的 JSON 給 powerbi 的工作簿建置器（build_powerbi_workbook）讀，
每個 key 對應一張 Power BI 資料表，欄位名與 .pbix 既有的表格對齊。

核心原則（對應專題主旨）：**只輸出資料庫裡的真實紀錄，不虛構任何數據。**
AI 衍生欄位（weak_topics / overall_feedback / course summary）若尚未產生，
就輸出空值/空陣列，不自行編造。

用法：
    python manage.py export_powerbi_json --output ../outputs/learnmate_powerbi_data.json
"""
import json
from collections import defaultdict
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import (
    Course,
    CourseChapter,
    CourseLesson,
    CourseSummary,
    Enrollment,
    LearningRecord,
    LessonProgress,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizQuestion,
)


def _iso(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _display_name(user):
    full = f"{user.last_name}{user.first_name}".strip()
    return full or user.username


def _role(user):
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', '') if profile else ''


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0


class Command(BaseCommand):
    help = '把 LearnMate 真實學習資料匯出成 Power BI 用的 JSON（只含實際紀錄，不補造）。'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True, help='輸出的 JSON 檔路徑')

    def handle(self, *args, **options):
        # ---- 一次撈出所有要用的資料（減少查詢次數）----
        users = list(User.objects.select_related('profile').order_by('id'))
        courses = list(Course.objects.select_related('teacher', 'category').order_by('id'))
        chapters = list(
            CourseChapter.objects.select_related('course').order_by('course_id', 'sort_order', 'id')
        )
        lessons = list(
            CourseLesson.objects.select_related('chapter', 'chapter__course')
            .order_by('chapter_id', 'sort_order', 'id')
        )
        enrollments = list(
            Enrollment.objects.select_related('student', 'course').order_by('id')
        )
        progress_rows = list(
            LessonProgress.objects.select_related('user', 'course', 'lesson').order_by('id')
        )
        learning_records = list(
            LearningRecord.objects.select_related('user', 'course', 'lesson').order_by('id')
        )
        summaries = list(CourseSummary.objects.select_related('course').order_by('course_id'))
        quizzes = list(
            Quiz.objects.select_related('chapter', 'chapter__course').order_by('id')
        )
        questions = list(
            QuizQuestion.objects.select_related('quiz', 'quiz__chapter').order_by('quiz_id', 'sort_order', 'id')
        )
        attempts = list(
            QuizAttempt.objects.select_related('user', 'quiz', 'quiz__chapter', 'quiz__chapter__course')
            .order_by('user_id', 'quiz_id', 'created_at', 'id')
        )
        answers = list(
            QuizAnswer.objects.select_related('attempt', 'question', 'question__quiz', 'question__quiz__chapter')
            .order_by('attempt_id', 'question__sort_order', 'id')
        )

        # ---- 常用對照表 ----
        quiz_course = {q.id: q.chapter.course_id for q in quizzes}
        question_topic = {qq.id: (qq.topic_tag or '') for qq in questions}

        # 每個 attempt 的作答次數排名（同一人同一測驗，依時間排）
        by_user_quiz = defaultdict(list)
        for a in attempts:
            by_user_quiz[(a.user_id, a.quiz_id)].append(a)
        attempt_meta = {}  # attempt_id -> (attempt_number, previous_score, is_latest)
        for key, group in by_user_quiz.items():
            group.sort(key=lambda x: (x.created_at, x.id))
            for idx, a in enumerate(group):
                prev = group[idx - 1].score if idx > 0 else None
                attempt_meta[a.id] = (idx + 1, prev, idx == len(group) - 1)

        data = {'generated_at': _iso(timezone.now())}

        # ---- 1. students ----
        data['students'] = [{
            'student_id': u.id,
            'username': u.username,
            'display_name': _display_name(u),
            'role': _role(u),
            'is_active': u.is_active,
            'date_joined': _iso(u.date_joined),
        } for u in users]

        # ---- 2. courses ----
        data['courses'] = [{
            'course_id': c.id,
            'course_title': c.title,
            'teacher_id': c.teacher_id,
            'teacher_name': _display_name(c.teacher),
            'category': c.category.name if c.category else None,
            'level': c.level,
            'is_published': c.is_published,
            'created_at': _iso(c.created_at),
        } for c in courses]

        # ---- 3. chapters ----
        data['chapters'] = [{
            'chapter_id': ch.id,
            'course_id': ch.course_id,
            'chapter_title': ch.title,
            'sort_order': ch.sort_order,
            'created_at': _iso(ch.created_at),
        } for ch in chapters]

        # ---- 4. lessons ----
        data['lessons'] = [{
            'lesson_id': l.id,
            'chapter_id': l.chapter_id,
            'lesson_title': l.title,
            'duration_minutes': l.duration_minutes,
            'sort_order': l.sort_order,
            'is_free_preview': l.is_free_preview,
            'created_at': _iso(l.created_at),
        } for l in lessons]

        # ---- 5. enrollments ----
        data['enrollments'] = [{
            'enrollment_id': e.id,
            'student_id': e.student_id,
            'course_id': e.course_id,
            'purchased_at': _iso(e.purchased_at),
        } for e in enrollments]

        # ---- 6. lesson_progress ----
        lp_out = []
        for p in progress_rows:
            duration = p.duration or 0
            replayed = p.replayed_seconds or 0
            total_watch = p.watched_seconds + replayed
            lp_out.append({
                'progress_id': p.id,
                'student_id': p.user_id,
                'course_id': p.course_id,
                'lesson_id': p.lesson_id,
                'watched_seconds': p.watched_seconds,
                'total_watch_seconds': total_watch,
                'duration_seconds': duration,
                'watch_rate': _rate(min(p.watched_seconds, duration), duration) if duration else 0,
                'view_count': p.view_count,
                'page_open_count': p.page_open_count,
                'replayed_seconds': replayed,
                'rewatch_ratio': _rate(replayed, duration) if duration else 0,
                'last_position_seconds': p.last_position,
                'is_completed': p.is_completed,
                'updated_at': _iso(p.updated_at),
            })
        data['lesson_progress'] = lp_out

        # ---- 7. learning_records ----
        data['learning_records'] = [{
            'learning_record_id': r.id,
            'student_id': r.user_id,
            'course_id': r.course_id,
            'lesson_id': r.lesson_id,
            'minutes': r.minutes,
            'watched_at': _iso(r.watched_at),
        } for r in learning_records]

        # ---- 8. course_summaries ----
        data['course_summaries'] = [{
            'summary_id': s.id,
            'course_id': s.course_id,
            'summary': s.summary,
            'core_concept_count': len(s.core_concepts or []),
            'key_term_count': len(s.key_terms or []),
            'created_at': _iso(s.created_at),
            'updated_at': _iso(s.updated_at),
        } for s in summaries]

        # ---- 9. quizzes ----
        data['quizzes'] = [{
            'quiz_id': q.id,
            'course_id': quiz_course.get(q.id),
            'quiz_type': q.quiz_type,
            'source_result_id': q.source_attempt_id,
            'created_by_id': None,
            'created_at': _iso(q.created_at),
        } for q in quizzes]

        # ---- 10. questions ----
        data['questions'] = [{
            'question_id': qq.id,
            'quiz_id': qq.quiz_id,
            'question_order': qq.sort_order,
            'question_text': qq.question_text,
            'topic_tag': qq.topic_tag or '',
            'correct_index': qq.correct_index,
            'explanation': qq.explanation,
        } for qq in questions]

        # ---- 11. quiz_results（= QuizAttempt）----
        qr_out = []
        for a in attempts:
            number, prev_score, is_latest = attempt_meta.get(a.id, (1, None, True))
            change = (a.score - prev_score) if prev_score is not None else None
            qr_out.append({
                'result_id': a.id,
                'student_id': a.user_id,
                'quiz_id': a.quiz_id,
                'course_id': quiz_course.get(a.quiz_id),
                'quiz_type': a.quiz.quiz_type,
                'source_result_id': a.quiz.source_attempt_id,
                'accuracy_rate': round(a.accuracy_rate, 4),
                'score_percent': a.score,
                'attempt_number': number,
                'previous_score_percent': prev_score,
                'score_change_percent': change,
                'is_latest_attempt': is_latest,
                'weak_topic_count': len(a.weak_topics or []),
                'strong_topic_count': len(a.strong_topics or []),
                'overall_feedback': a.overall_feedback or '',
                'submitted_at': _iso(a.created_at),
            })
        data['quiz_results'] = qr_out

        # ---- 12. answers ----
        data['answers'] = [{
            'answer_id': ans.id,
            'result_id': ans.attempt_id,
            'student_id': ans.attempt.user_id,
            'course_id': quiz_course.get(ans.question.quiz_id),
            'quiz_id': ans.question.quiz_id,
            'question_id': ans.question_id,
            'topic_tag': question_topic.get(ans.question_id, ''),
            'selected_index': ans.selected_index,
            'correct_index': ans.question.correct_index,
            'is_correct': ans.is_correct,
        } for ans in answers]

        # ---- 13. weak_topics（展開 QuizAttempt.weak_topics JSON）----
        wt_out = []
        for a in attempts:
            for item in (a.weak_topics or []):
                if not isinstance(item, dict):
                    continue
                wt_out.append({
                    'result_id': a.id,
                    'student_id': a.user_id,
                    'course_id': quiz_course.get(a.quiz_id),
                    'quiz_id': a.quiz_id,
                    'topic': item.get('topic', ''),
                    'issue_description': item.get('issue_description', ''),
                    'severity': item.get('severity', ''),
                    'submitted_at': _iso(a.created_at),
                })
        data['weak_topics'] = wt_out

        # ---- 14. remedial_comparisons（同一人同一測驗：第一次 vs 最後一次）----
        rc_out = []
        for (user_id, quiz_id), group in by_user_quiz.items():
            if len(group) < 2:
                continue
            group.sort(key=lambda x: (x.created_at, x.id))
            before, after = group[0], group[-1]
            rc_out.append({
                'student_id': user_id,
                'course_id': quiz_course.get(quiz_id),
                'before_result_id': before.id,
                'after_result_id': after.id,
                'before_accuracy_rate': round(before.accuracy_rate, 4),
                'after_accuracy_rate': round(after.accuracy_rate, 4),
                'improvement_rate': round(after.accuracy_rate - before.accuracy_rate, 4),
                'before_submitted_at': _iso(before.created_at),
                'after_submitted_at': _iso(after.created_at),
            })
        data['remedial_comparisons'] = rc_out

        # ---- 預先聚合：每課的單元、每人每課的進度與作答 ----
        course_lessons = defaultdict(list)       # course_id -> [lesson]
        for l in lessons:
            course_lessons[l.chapter.course_id].append(l)

        prog_by_sc = defaultdict(list)           # (student, course) -> [progress]
        prog_by_course = defaultdict(list)       # course -> [progress]
        for p in progress_rows:
            prog_by_sc[(p.user_id, p.course_id)].append(p)
            prog_by_course[p.course_id].append(p)

        att_by_sc = defaultdict(list)            # (student, course) -> [attempt]
        att_by_course = defaultdict(list)        # course -> [attempt]
        for a in attempts:
            cid = quiz_course.get(a.quiz_id)
            att_by_sc[(a.user_id, cid)].append(a)
            att_by_course[cid].append(a)

        enroll_by_course = defaultdict(set)      # course -> {student}
        sc_pairs = set()
        for e in enrollments:
            enroll_by_course[e.course_id].add(e.student_id)
            sc_pairs.add((e.student_id, e.course_id))
        # 也把有進度或作答但沒選課紀錄的組合納入（確保不漏資料）
        sc_pairs |= set(prog_by_sc.keys()) | set(att_by_sc.keys())

        def _watch_rate(p):
            return min(p.watched_seconds, p.duration) / p.duration if p.duration else 0

        # ---- 15. student_course_metrics ----
        scm_out = []
        for (student_id, course_id) in sorted(sc_pairs):
            if course_id is None:
                continue
            c_lessons = course_lessons.get(course_id, [])
            lesson_count = len(c_lessons)
            progs = prog_by_sc.get((student_id, course_id), [])
            played = len({p.lesson_id for p in progs})
            completed = sum(1 for p in progs if p.is_completed)
            watch_rates = [_watch_rate(p) for p in progs if p.duration]
            atts = sorted(att_by_sc.get((student_id, course_id), []), key=lambda x: (x.created_at, x.id))
            latest = atts[-1] if atts else None
            prev = atts[-2] if len(atts) >= 2 else None
            scm_out.append({
                'student_id': student_id,
                'course_id': course_id,
                'lesson_count': lesson_count,
                'played_lesson_count': played,
                'completed_lesson_count': completed,
                'lesson_completion_rate': _rate(completed, lesson_count),
                'average_watch_rate': round(sum(watch_rates) / len(watch_rates), 4) if watch_rates else 0,
                'quiz_attempt_count': len(atts),
                'historical_average_score_percent': round(sum(a.score for a in atts) / len(atts), 1) if atts else None,
                'latest_score_percent': latest.score if latest else None,
                'previous_score_percent': prev.score if prev else None,
                'latest_score_change_percent': (latest.score - prev.score) if (latest and prev) else None,
                'latest_quiz_type': latest.quiz.quiz_type if latest else None,
                'latest_weak_topic_count': len(latest.weak_topics or []) if latest else None,
                'historical_weakness_mentions': sum(len(a.weak_topics or []) for a in atts),
                'latest_submitted_at': _iso(latest.created_at) if latest else None,
            })
        data['student_course_metrics'] = scm_out

        # ---- 16. course_health ----
        ch_out = []
        for c in courses:
            c_lessons = course_lessons.get(c.id, [])
            lesson_count = len(c_lessons)
            enrolled = len(enroll_by_course.get(c.id, set()))
            progs = prog_by_course.get(c.id, [])
            completed = sum(1 for p in progs if p.is_completed)
            atts = att_by_course.get(c.id, [])
            accuracies = [a.accuracy_rate for a in atts]
            ch_out.append({
                'course_id': c.id,
                'enrolled_students': enrolled,
                'lesson_count': lesson_count,
                'recorded_progress_count': len(progs),
                'completed_lesson_count': completed,
                'lesson_completion_rate': _rate(completed, enrolled * lesson_count) if (enrolled and lesson_count) else 0,
                'quiz_result_count': len(atts),
                'average_quiz_accuracy_rate': round(sum(accuracies) / len(accuracies), 4) if accuracies else 0,
                'weakness_mentions': sum(len(a.weak_topics or []) for a in atts),
            })
        data['course_health'] = ch_out

        # ---- 17. topic_stats（每課 × 知識點）----
        # 題目依 (course, topic) 分組
        topic_questions = defaultdict(set)       # (course, topic) -> {question_id}
        for qq in questions:
            topic = qq.topic_tag or ''
            if not topic:
                continue
            cid = quiz_course.get(qq.quiz_id)
            topic_questions[(cid, topic)].add(qq.id)
        # 作答依題目歸到 topic
        topic_answers = defaultdict(lambda: [0, 0])  # (course, topic) -> [answer_count, wrong_count]
        for ans in answers:
            topic = question_topic.get(ans.question_id, '')
            if not topic:
                continue
            cid = quiz_course.get(ans.question.quiz_id)
            topic_answers[(cid, topic)][0] += 1
            if not ans.is_correct:
                topic_answers[(cid, topic)][1] += 1
        # 弱點被提及次數
        topic_mentions = defaultdict(int)        # (course, topic) -> count
        for a in attempts:
            cid = quiz_course.get(a.quiz_id)
            for item in (a.weak_topics or []):
                if isinstance(item, dict) and item.get('topic'):
                    topic_mentions[(cid, item['topic'])] += 1

        ts_keys = set(topic_questions) | set(topic_answers) | set(topic_mentions)
        ts_out = []
        for (cid, topic) in sorted(ts_keys, key=lambda k: (k[0] or 0, k[1])):
            ans_count, wrong_count = topic_answers.get((cid, topic), [0, 0])
            ts_out.append({
                'course_id': cid,
                'topic': topic,
                'question_count': len(topic_questions.get((cid, topic), set())),
                'answer_count': ans_count,
                'wrong_answer_count': wrong_count,
                'error_rate': _rate(wrong_count, ans_count),
                'weakness_mentions': topic_mentions.get((cid, topic), 0),
            })
        data['topic_stats'] = ts_out

        # ---- 寫檔 ----
        output = Path(options['output']).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        counts = {k: (len(v) if isinstance(v, list) else 1) for k, v in data.items() if k != 'generated_at'}
        self.stdout.write(self.style.SUCCESS(f'Power BI JSON 已匯出：{output}'))
        self.stdout.write('各表列數：' + ', '.join(f'{k}={n}' for k, n in counts.items()))
