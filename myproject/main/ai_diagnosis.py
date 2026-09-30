"""AI 學習診斷：把學生在一門課的真實學習數據（完成率、觀看、Quiz 錯題）
整理成結構化資料，交給 Azure OpenAI 產生學習弱點診斷與個人化建議。

核心原則：AI 只能「解讀」下面餵進去的真實數字，不得虛構任何未提供的數據。
"""
from . import ai_assistant


def build_learning_profile(user, course):
    """蒐集並整理某位學生在這門課的真實學習數據，回傳結構化 dict。"""
    from .models import (
        CourseChapter, CourseLesson, LessonProgress, Quiz, QuizAttempt,
    )

    chapters_data = []
    total_lessons = 0
    total_completed = 0

    chapters = (
        CourseChapter.objects.filter(course=course)
        .prefetch_related('lessons')
        .order_by('sort_order')
    )

    for chapter in chapters:
        lessons = list(chapter.lessons.all())
        lesson_ids = [l.id for l in lessons]
        n_lessons = len(lessons)
        total_lessons += n_lessons

        progresses = list(
            LessonProgress.objects.filter(user=user, lesson_id__in=lesson_ids)
        )
        completed = sum(1 for p in progresses if p.is_completed)
        total_completed += completed
        watch_percents = [p.percent() for p in progresses] if progresses else []
        avg_watch = round(sum(watch_percents) / len(watch_percents)) if watch_percents else 0

        chapter_info = {
            'title': chapter.title,
            'sort_order': chapter.sort_order,
            'lesson_count': n_lessons,
            'completed_count': completed,
            'completion_pct': round(completed / n_lessons * 100) if n_lessons else 0,
            'avg_watch_pct': avg_watch,
            'quiz': None,
        }

        quiz = Quiz.objects.filter(chapter=chapter, is_published=True).first()
        if quiz:
            attempt = (
                QuizAttempt.objects.filter(user=user, quiz=quiz)
                .order_by('-created_at').first()
            )
            attempts_count = QuizAttempt.objects.filter(user=user, quiz=quiz).count()
            if attempt:
                wrong = []
                for ans in attempt.answers.select_related('question').all():
                    if not ans.is_correct:
                        q = ans.question
                        opts = q.options or []
                        your = opts[ans.selected_index] if 0 <= ans.selected_index < len(opts) else '（未作答）'
                        correct = opts[q.correct_index] if 0 <= q.correct_index < len(opts) else ''
                        wrong.append({
                            'question': q.question_text,
                            'your_answer': your,
                            'correct_answer': correct,
                        })
                chapter_info['quiz'] = {
                    'score': attempt.score,
                    'correct_count': attempt.correct_count,
                    'total_count': attempt.total_count,
                    'attempts_count': attempts_count,
                    'wrong_questions': wrong,
                }

        chapters_data.append(chapter_info)

    return {
        'course_title': course.title,
        'overall_completion_pct': round(total_completed / total_lessons * 100) if total_lessons else 0,
        'total_lessons': total_lessons,
        'completed_lessons': total_completed,
        'chapters': chapters_data,
    }


def _profile_to_text(profile):
    """把結構化 profile 轉成餵給模型的可讀文字。"""
    lines = [
        f"課程：{profile['course_title']}",
        f"整體完成率：{profile['overall_completion_pct']}%"
        f"（{profile['completed_lessons']}/{profile['total_lessons']} 個單元）",
        '',
        '各章節學習狀況：',
    ]
    for ch in profile['chapters']:
        lines.append(
            f"　第 {ch['sort_order']} 章「{ch['title']}」："
            f"完成率 {ch['completion_pct']}%"
            f"（{ch['completed_count']}/{ch['lesson_count']} 單元）、"
            f"平均影片觀看完成度 {ch['avg_watch_pct']}%"
        )
        quiz = ch['quiz']
        if quiz:
            lines.append(
                f"　　測驗：{quiz['score']} 分"
                f"（答對 {quiz['correct_count']}/{quiz['total_count']} 題，"
                f"共作答 {quiz['attempts_count']} 次）"
            )
            if quiz['wrong_questions']:
                lines.append('　　答錯的題目：')
                for w in quiz['wrong_questions']:
                    lines.append(
                        f"　　　・「{w['question']}」"
                        f"（學生答：{w['your_answer']}；正解：{w['correct_answer']}）"
                    )
            else:
                lines.append('　　測驗全部答對。')
        else:
            lines.append('　　（此章尚無測驗或未作答）')
    return '\n'.join(lines)


def diagnose(user, course):
    """回傳 {'ok': bool, 'diagnosis'/'error': str, 'weak_topics': list, 'profile': dict}。"""
    if not ai_assistant.is_enabled():
        return {'ok': False, 'error': 'AI 診斷尚未啟用（管理者尚未設定 API 金鑰）。'}

    profile = build_learning_profile(user, course)

    if profile['total_lessons'] == 0:
        return {'ok': False, 'error': '這門課目前沒有單元，無法進行學習診斷。'}
    if profile['completed_lessons'] == 0 and not any(ch['quiz'] for ch in profile['chapters']):
        return {'ok': False, 'error': '你還沒有足夠的學習紀錄，先看幾個單元或做一次測驗再回來診斷吧！'}

    system = (
        '你是一位專業、溫暖的學習診斷老師。下面是某位學生在一門線上課程的「真實」學習數據。'
        '請「只」根據這些數據分析，絕對不要虛構任何未提供的數字或內容。\n'
        '你的任務：\n'
        '1. 具體指出這位學生目前的學習弱點——是哪一章、哪些概念（可從答錯的題目推斷概念）。\n'
        '2. 說明你的判斷依據（例如完成率低、測驗分數低、某類題目一直答錯）。\n'
        '3. 給 2～4 點可立即執行的下一步建議（要具體，例如「重看第 3 章並重做測驗」）。\n'
        '4. 若數據顯示學生表現良好，也要如實肯定，不要硬找問題。\n'
        '語氣親切、用繁體中文、用 Markdown 條列，精簡不要冗長。\n'
        '最後「另起一行」用 ||| 分隔列出 1～3 個最需要加強的「弱點主題關鍵詞」，'
        '格式：|||關鍵詞1|||關鍵詞2（例如 |||List|||INNER JOIN）。若無明顯弱點則不要加這行。'
    )
    user_msg = _profile_to_text(profile)

    try:
        reply = ai_assistant._call_model(system, [{'role': 'user', 'content': user_msg}])
    except ai_assistant._AIError as exc:
        return {'ok': False, 'error': str(exc)}

    diagnosis, weak_topics = _parse_weak_topics(reply)
    return {
        'ok': True,
        'diagnosis': diagnosis,
        'weak_topics': weak_topics,
        'profile': profile,
    }


def _parse_weak_topics(text):
    if '|||' not in text:
        return text.strip(), []
    parts = text.split('|||')
    body = parts[0].strip()
    topics = [t.strip() for t in parts[1:] if t.strip()]
    return body, topics[:3]
