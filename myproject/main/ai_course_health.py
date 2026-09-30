"""教師端 AI 課程健康度：聚合「全體學生」在一門課各章節的真實學習數據
（完成率、平均測驗分數、最常答錯的題目），交給 Azure OpenAI 解讀，
找出學習瓶頸章節並給教師改善建議。

Power BI 負責「呈現數據」，這裡的 AI 負責「解讀數據」。
所有數字皆為資料庫真實聚合，AI 只做解讀、不虛構。
"""
from . import ai_assistant


def build_course_health_stats(course):
    """聚合全體學生在這門課各章節的真實學習數據，回傳結構化 dict。"""
    from .models import (
        CourseChapter, Enrollment, LessonProgress, Quiz, QuizAttempt, QuizAnswer,
    )

    student_ids = list(
        Enrollment.objects.filter(course=course).values_list('student_id', flat=True)
    )
    n_students = len(student_ids)

    chapters_data = []
    chapters = (
        CourseChapter.objects.filter(course=course)
        .prefetch_related('lessons').order_by('sort_order')
    )

    for chapter in chapters:
        lessons = list(chapter.lessons.all())
        lesson_ids = [l.id for l in lessons]
        n_lessons = len(lessons)

        # 完成率：全體學生已完成的單元數 / （學生數 × 單元數）
        completion_pct = 0
        if n_students and n_lessons:
            done = LessonProgress.objects.filter(
                lesson_id__in=lesson_ids, user_id__in=student_ids, is_completed=True
            ).count()
            completion_pct = round(done / (n_students * n_lessons) * 100)

        chapter_info = {
            'title': chapter.title,
            'sort_order': chapter.sort_order,
            'lesson_count': n_lessons,
            'completion_pct': completion_pct,
            'quiz': None,
        }

        quiz = Quiz.objects.filter(chapter=chapter, is_published=True).first()
        if quiz:
            # 每位學生取「最近一次」作答，算平均分與通過率
            latest_by_student = {}
            for att in (
                QuizAttempt.objects.filter(quiz=quiz, user_id__in=student_ids)
                .order_by('user_id', '-created_at')
            ):
                if att.user_id not in latest_by_student:
                    latest_by_student[att.user_id] = att
            attempts = list(latest_by_student.values())
            if attempts:
                avg_score = round(sum(a.score for a in attempts) / len(attempts))
                passed = sum(1 for a in attempts if a.score >= quiz.pass_score)
                pass_rate = round(passed / len(attempts) * 100)

                # 最常答錯的題目（跨這些最近作答）
                attempt_ids = [a.id for a in attempts]
                wrong_counter = {}
                total_counter = {}
                for ans in QuizAnswer.objects.filter(
                    attempt_id__in=attempt_ids
                ).select_related('question'):
                    qt = ans.question.question_text
                    total_counter[qt] = total_counter.get(qt, 0) + 1
                    if not ans.is_correct:
                        wrong_counter[qt] = wrong_counter.get(qt, 0) + 1
                hardest = sorted(
                    (
                        {'question': qt,
                         'wrong_rate': round(wrong_counter.get(qt, 0) / total_counter[qt] * 100)}
                        for qt in total_counter
                    ),
                    key=lambda x: x['wrong_rate'], reverse=True,
                )[:2]
                hardest = [h for h in hardest if h['wrong_rate'] > 0]

                chapter_info['quiz'] = {
                    'avg_score': avg_score,
                    'pass_rate': pass_rate,
                    'attempt_students': len(attempts),
                    'hardest_questions': hardest,
                }

        chapters_data.append(chapter_info)

    return {
        'course_title': course.title,
        'student_count': n_students,
        'chapters': chapters_data,
    }


def _stats_to_text(stats):
    lines = [
        f"課程：{stats['course_title']}",
        f"選課學生數：{stats['student_count']} 人",
        '',
        '各章節數據：',
    ]
    for ch in stats['chapters']:
        line = (
            f"　第 {ch['sort_order']} 章「{ch['title']}」："
            f"完成率 {ch['completion_pct']}%"
        )
        quiz = ch['quiz']
        if quiz:
            line += (
                f"、測驗平均 {quiz['avg_score']} 分、"
                f"通過率 {quiz['pass_rate']}%"
                f"（{quiz['attempt_students']} 人作答）"
            )
        else:
            line += "、（無測驗或無人作答）"
        lines.append(line)
        if quiz and quiz['hardest_questions']:
            for h in quiz['hardest_questions']:
                lines.append(f"　　最常答錯：「{h['question']}」（答錯率 {h['wrong_rate']}%）")
    return '\n'.join(lines)


def analyze(course):
    """回傳 {'ok': bool, 'analysis'/'error': str, 'stats': dict}。"""
    if not ai_assistant.is_enabled():
        return {'ok': False, 'error': 'AI 尚未啟用（管理者尚未設定 API 金鑰）。'}

    stats = build_course_health_stats(course)
    if stats['student_count'] == 0:
        return {'ok': False, 'error': '這門課目前還沒有學生選課，無法進行課程健康度分析。'}
    if not stats['chapters']:
        return {'ok': False, 'error': '這門課目前沒有章節。'}

    system = (
        '你是一位課程教學顧問。下面是一門線上課程「全體學生」的真實學習數據。'
        '請「只」根據這些數據分析，絕對不要虛構任何未提供的數字。\n'
        '你的任務：\n'
        '1. 指出這門課目前的「學習瓶頸章節」——哪一章的學生表現明顯較差（完成率低、測驗平均低、通過率低、某題答錯率高）。\n'
        '2. 說明判斷依據（引用實際數字）。\n'
        '3. 推測可能原因（教材難度、概念抽象、測驗題目等）。\n'
        '4. 給教師 2～4 點具體可執行的改善建議（例如補充範例、調整教材、修改某題）。\n'
        '若整體表現良好也要如實說明。語氣專業、用繁體中文、用 Markdown 條列、精簡。'
    )
    user_msg = _stats_to_text(stats)

    try:
        analysis = ai_assistant._call_model(system, [{'role': 'user', 'content': user_msg}])
    except ai_assistant._AIError as exc:
        return {'ok': False, 'error': str(exc)}

    return {'ok': True, 'analysis': analysis.strip(), 'stats': stats}
