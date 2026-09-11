"""AI 課程助教：以單堂課程的公開資訊為依據，回答已購買學員的提問。

設計原則：
- 金鑰或 SDK 未就緒時回傳友善訊息，不讓其他功能壞掉（懶載入 anthropic）。
- 只把「這堂課」的資訊餵給模型，避免答非所問；找不到答案就誠實說明。
- 模型可用環境變數 AI_ASSISTANT_MODEL 覆寫（預設 claude-opus-5；想省成本可設 claude-haiku-4-5）。
"""
from django.conf import settings


def is_enabled():
    return bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def build_course_context(course):
    """把課程的標題、簡介、講師與章節單元整理成給模型的背景文字。"""
    lines = [f'課程名稱：{course.title}']
    try:
        lines.append(f'講師：{course.teacher.profile.display_name}')
        if course.teacher.profile.bio:
            lines.append(f'講師簡介：{course.teacher.profile.bio}')
    except Exception:
        pass
    if course.category:
        lines.append(f'分類：{course.category.name}')
    lines.append(f'課程簡介：{course.description}')

    lines.append('課程大綱：')
    for chapter in course.chapters.prefetch_related('lessons').all():
        lines.append(f'  章節：{chapter.title}')
        for lesson in chapter.lessons.all():
            lines.append(f'    - 單元：{lesson.title}')
    return '\n'.join(lines)


def answer_course_question(course, question):
    """回傳 {'ok': bool, 'answer'/'error': str}。"""
    if not is_enabled():
        return {'ok': False, 'error': 'AI 助教尚未啟用（管理者尚未設定 API 金鑰）。'}

    question = (question or '').strip()
    if not question:
        return {'ok': False, 'error': '請先輸入問題。'}

    try:
        import anthropic
    except ImportError:
        return {'ok': False, 'error': 'AI 助教套件尚未安裝（pip install anthropic）。'}

    context = build_course_context(course)
    system = (
        f'你是線上課程「{course.title}」的 AI 課程助教。'
        '請「只」根據下面提供的課程資訊，用繁體中文、親切且簡潔地回答學生的問題。'
        '若問題超出課程範圍或提供的資訊不足以回答，請誠實說明並建議學生到課程問答區詢問講師，不要編造內容。\n\n'
        f'=== 課程資訊 ===\n{context}'
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = getattr(settings, 'AI_ASSISTANT_MODEL', 'claude-opus-5')
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            output_config={'effort': 'low'},
            messages=[{'role': 'user', 'content': question}],
        )
        if getattr(response, 'stop_reason', None) == 'refusal':
            return {'ok': False, 'error': '這個問題我無法回答，換個方式問問看？'}
        answer = ''.join(b.text for b in response.content if getattr(b, 'type', None) == 'text')
        return {'ok': True, 'answer': answer.strip() or '（沒有產生回覆，請再試一次）'}
    except anthropic.RateLimitError:
        return {'ok': False, 'error': 'AI 助教目前使用量較高，請稍後再試。'}
    except anthropic.AuthenticationError:
        return {'ok': False, 'error': 'AI 助教金鑰無效，請聯絡管理者。'}
    except Exception as exc:  # noqa: BLE001 - 對外一律回傳友善訊息
        return {'ok': False, 'error': f'AI 助教暫時無法使用（{type(exc).__name__}）。'}
