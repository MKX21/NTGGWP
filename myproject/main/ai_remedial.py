"""AI 自適性補救 Quiz：根據學生在某章測驗的「真實錯題」與學習弱點，
讓 Azure OpenAI 生成針對弱點概念的補救練習題（附解析），供學生加強後重測。

補救題是「即時生成的練習」，附正解與解析讓學生立即學習；真正證明學習成效的
「前後分數對照」則來自學生在原章節測驗的第一次與第二次真實作答成績。
"""
import json

from . import ai_assistant


def _latest_wrong_context(user, chapter):
    """取得學生在這章測驗最近一次作答的錯題與弱點，回傳 (wrong_list, score, has_quiz)。"""
    from .models import Quiz, QuizAttempt

    quiz = Quiz.objects.filter(chapter=chapter, is_published=True).first()
    if not quiz:
        return [], None, False

    attempt = (
        QuizAttempt.objects.filter(user=user, quiz=quiz)
        .order_by('-created_at').first()
    )
    if not attempt:
        return [], None, True

    wrong = []
    for ans in attempt.answers.select_related('question').all():
        if not ans.is_correct:
            q = ans.question
            opts = q.options or []
            correct = opts[q.correct_index] if 0 <= q.correct_index < len(opts) else ''
            wrong.append({'question': q.question_text, 'correct_answer': correct})
    return wrong, attempt.score, True


def generate_remedial(user, chapter, num_questions=4):
    """回傳 {'ok': bool, 'questions'/'error': ..., 'based_on': [...]}。
    questions: [{'question_text','options','correct_index','explanation'}]"""
    if not ai_assistant.is_enabled():
        return {'ok': False, 'error': 'AI 尚未啟用（管理者尚未設定 API 金鑰）。'}

    wrong, score, has_quiz = _latest_wrong_context(user, chapter)
    if not has_quiz:
        return {'ok': False, 'error': '這個章節還沒有測驗。'}
    if not wrong:
        return {'ok': False, 'error': '你在這章測驗沒有答錯的題目，不需要補救練習！'}

    course_title = chapter.course.title
    wrong_text = '\n'.join(
        f"・題目：{w['question']}（正解：{w['correct_answer']}）" for w in wrong
    )

    system = (
        f'你是「{course_title}」課程的出題老師。學生在「{chapter.title}」的測驗答錯了下列題目，'
        '請針對這些題目背後的「概念弱點」，設計補救練習題，幫助學生真正弄懂。\n'
        f'請生成 {num_questions} 題繁體中文「單選題」，難度由淺入深（先基礎、再應用）。\n'
        '嚴格要求：\n'
        '1. 每題 4 個選項，只有 1 個正確。\n'
        '2. 針對學生答錯的概念，換個角度或情境出題，不要照抄原題。\n'
        '3. 每題附「解析」說明為什麼正解是對的。\n'
        '4. 只能回傳「純 JSON 陣列」，不要有任何多餘文字或 ```markdown 標記。\n'
        '格式範例：\n'
        '[{"question_text":"題目","options":["A","B","C","D"],"correct_index":0,"explanation":"解析"}]'
    )
    user_msg = f'學生答錯的題目：\n{wrong_text}'

    try:
        reply = ai_assistant._call_model(system, [{'role': 'user', 'content': user_msg}])
    except ai_assistant._AIError as exc:
        return {'ok': False, 'error': str(exc)}

    questions = _parse_questions(reply)
    if not questions:
        return {'ok': False, 'error': 'AI 生成的題目格式異常，請再試一次。'}

    return {
        'ok': True,
        'questions': questions,
        'based_on_score': score,
        'wrong_count': len(wrong),
    }


def _parse_questions(reply):
    """從模型回覆解析出題目陣列，容錯處理 code fence 與前後雜訊。"""
    text = reply.strip()
    if text.startswith('```'):
        text = text.split('```', 2)[1] if text.count('```') >= 2 else text.strip('`')
        if text.lstrip().lower().startswith('json'):
            text = text.lstrip()[4:]
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except (ValueError, TypeError):
        return []

    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        q = str(item.get('question_text', '')).strip()
        opts = item.get('options')
        ci = item.get('correct_index')
        if not q or not isinstance(opts, list) or len(opts) < 2:
            continue
        try:
            ci = int(ci)
        except (TypeError, ValueError):
            continue
        if not (0 <= ci < len(opts)):
            continue
        cleaned.append({
            'question_text': q,
            'options': [str(o) for o in opts],
            'correct_index': ci,
            'explanation': str(item.get('explanation', '')).strip(),
        })
    return cleaned
