"""AI 課程助教：以單堂課程的公開資訊為依據，回答已購買學員的提問。

設計原則：
- 金鑰或 SDK 未就緒時回傳友善訊息，不讓其他功能壞掉（懶載入 SDK）。
- 只把「這堂課」的資訊餵給模型，避免答非所問；找不到答案就誠實說明。
- 支援兩種後端，用哪一種由 .env 決定：
    - 設定 GEMINI_API_KEY → 用 Google Gemini（模型可用 GEMINI_MODEL 覆寫，預設 gemini-3.8-flash）
    - 設定 ANTHROPIC_API_KEY → 用 Claude（模型可用 AI_ASSISTANT_MODEL 覆寫，預設 claude-opus-5）
    - 兩個都設定時，用 AI_PROVIDER=gemini 或 AI_PROVIDER=anthropic 明確指定；
      沒指定就優先用 Gemini。

本檔也提供「課程問答」（CourseQuestion/CourseAnswer）的延伸功能：
- auto_answer_question：學生發問後，自動以 AI 助教身分產生一則回答。
這是盡力而為 —— 沒設金鑰、SDK 未安裝或呼叫失敗時安靜地回傳 None，
不影響提問／回答本身的既有流程。

另外提供 answer_platform_question：首頁用的平台助手，回答平台 FAQ（定價／
折扣／退款／課程上架規則等）並根據目前上架課程做推薦，不綁定單一課程。
"""
import time

from django.conf import settings

AI_BOT_USERNAME = 'ai_assistant'


# =========================
# 常見問題（FAQ）—— 零 API 流量消耗
# =========================
# 命中就直接回傳固定答案，完全不呼叫任何 AI 後端：
# 不用等模型回應、不吃 token 額度，也不受供應商限流（429）影響。
# 前端（首頁／課程頁的 AI 助手面板）會把這份清單渲染成快速按鈕；
# views.py 的 ask_ai / ask_platform_ai 則在呼叫模型「之前」用 match_platform_faq
# 比對使用者手動輸入的文字，命中一樣直接回覆、不送出 API 請求。
PLATFORM_FAQS = [
    {
        'id': 'watch-course',
        'label': '📺 如何觀看課程？',
        'question': '要怎麼觀看已購買的課程？',
        'keywords': ['觀看', '怎麼看課', '看課程', '如何看課', '播放', '上課方式', '手機看課', '怎麼上課', '怎麼看影片'],
        'answer': (
            '登入後點右上角「我的課程」，選擇已購買的課程即可進入課程頁，'
            '依章節／單元順序點選影片播放。課程為永久觀看權限，電腦與手機瀏覽器都能觀看，'
            '不需要另外安裝 App。'
        ),
    },
    {
        'id': 'payment',
        'label': '💳 付費方式介紹',
        'question': '平台支援哪些付費方式？',
        'keywords': ['付費', '付款', '怎麼付', '付款方式', '信用卡', '結帳', '怎麼買課', '購買方式'],
        'answer': (
            '結帳時可使用信用卡或第三方金流付款；課程會依「售價」計價'
            '（募資期間內優先套用早鳥價，其次是折扣價，兩者不疊加），'
            '平台促銷會再疊加在售價上，若有優惠券可於結帳頁輸入折抵碼折抵。'
        ),
    },
    {
        'id': 'course-missing',
        'label': '📚 課程遺失怎麼辦？',
        'question': '我買的課程不見了怎麼辦？',
        'keywords': ['課程不見', '找不到課程', '課程遺失', '買的課程不見', '課程消失', '課不見', '課不見了'],
        'answer': (
            '請先確認是用「購買當下」的同一個帳號登入，並到「我的課程」查看清單。'
            '若確定用對帳號仍看不到已購買的課程，可能是訂單尚未完成付款或已被退款，'
            '可到「我的訂單／我的退款」頁面查詢狀態，或聯絡課程講師／平台管理員協助處理。'
        ),
    },
    {
        'id': 'forgot-password',
        'label': '🔑 忘記帳號密碼',
        'question': '我忘記帳號或密碼了怎麼辦？',
        'keywords': ['忘記密碼', '忘記帳號', '密碼忘記', '登入不了', '無法登入', '找回密碼', '重設密碼'],
        'answer': (
            '忘記密碼：請到登入頁點選「忘記密碼」，輸入註冊時使用的 Email 以重設密碼。\n'
            '忘記帳號：帳號通常就是註冊時使用的 Email，若仍無法確認，請聯絡平台管理員協助查詢。'
        ),
    },
]


def match_platform_faq(question):
    """比對使用者輸入是否命中預設 FAQ，命中回傳該筆 FAQ dict，否則回傳 None。

    純字串比對，不呼叫任何 AI 後端；供 views.py 在呼叫模型之前先攔截用。
    """
    text = (question or '').strip().lower()
    if not text:
        return None
    for faq in PLATFORM_FAQS:
        for kw in faq['keywords']:
            if kw.lower() in text:
                return faq
    return None


class _AIError(Exception):
    """內部用：包一則已經是繁體中文、可直接顯示給使用者的錯誤訊息。"""


def _active_provider():
    """回傳目前應該使用的後端：'gemini' / 'anthropic' / None（都沒設定）。"""
    forced = (getattr(settings, 'AI_PROVIDER', '') or '').strip().lower()
    if forced in ('gemini', 'anthropic'):
        return forced
    if getattr(settings, 'GEMINI_API_KEY', ''):
        return 'gemini'
    if getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return 'anthropic'
    return None


def is_enabled():
    return _active_provider() is not None


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


def build_platform_context():
    """把平台使用須知與目前上架課程整理成給模型的背景文字（首頁平台助手用）。"""
    from .models import Course

    lines = ['=== 平台使用須知 ===']
    lines.append(
        '定價與折扣：每堂課有「定價」；「售價」是目前對外實際販售的價格，'
        '募資期間內優先取早鳥價，其次取折扣價（二者只取其一，不疊加）；'
        '平台促銷會再疊加在售價上；優惠券則疊加在促銷後的金額上，於結帳時輸入折抵碼使用。'
    )
    lines.append(
        '退款：平台提供開課後 7 天內不滿意可申請退費的保障。已付款的訂單可以在「我的退款」頁面提出申請，'
        '需經審核（課程講師或管理員）通過才會生效；退款會撤銷購課存取權，但學習紀錄與已寫的課程評價會保留。'
    )
    lines.append(
        '課程上架與可見性：未上架的課程只有課程講師本人、平台管理員、以及已購買過的學生看得到，'
        '其餘使用者看不到、也無法購買。'
    )
    lines.append(
        '角色：學生（購課、觀看、評價、提問）、講師（開課、管理課程內容、回答提問）、'
        '管理員（審核課程與退款、平台分析）。講師身分是由平台管理員在後台開通，不是自行申請切換。'
    )

    lines.append('')
    lines.append('=== 目前上架中的課程（可用於推薦） ===')
    courses = Course.objects.filter(is_published=True).select_related('category', 'teacher')
    if not courses:
        lines.append('（目前沒有上架中的課程）')
    for c in courses:
        desc = (c.description or '').strip().replace('\n', ' ')
        if len(desc) > 60:
            desc = desc[:60] + '…'
        cat = c.category.name if c.category else '未分類'
        try:
            price = int(c.get_effective_price())
            price_text = f'NT${price}'
        except Exception:
            price_text = '（價格未知）'
        lines.append(f'- 「{c.title}」（分類：{cat}，{price_text}）：{desc}')
    return '\n'.join(lines)


def answer_platform_question(question):
    """回傳 {'ok': bool, 'answer'/'error': str}。首頁平台助手：FAQ + 課程推薦，不綁定單一課程。"""
    if not is_enabled():
        return {'ok': False, 'error': 'AI 助教尚未啟用（管理者尚未設定 API 金鑰）。'}

    question = (question or '').strip()
    if not question:
        return {'ok': False, 'error': '請先輸入問題。'}

    context = build_platform_context()
    system = (
        '你是線上課程平台 EduFlow 的 AI 助手，負責兩件事：'
        '(1) 回答平台使用相關的常見問題（定價、折扣、退款、課程上架規則、角色權限等）；'
        '(2) 根據下面列出的「目前上架中的課程」推薦適合使用者需求的課程。'
        '請「只」根據下面提供的資訊回答，用繁體中文、親切且簡潔地回覆。'
        '如果使用者問的是某堂課的細節（例如課程大綱、單元內容），你只知道課程簡介，'
        '請誠實說明並建議使用者點進該課程頁面查看，或用該課程內的 AI 課程助教詢問細節。'
        '若問題超出平台範圍或提供的資訊不足以回答，請誠實說明，不要編造內容。\n\n'
        f'{context}'
    )

    try:
        answer = _call_model(system, question)
    except _AIError as exc:
        return {'ok': False, 'error': str(exc)}
    return {'ok': True, 'answer': answer or '（沒有產生回覆，請再試一次）'}


def _call_claude(system, user_message):
    try:
        import anthropic
    except ImportError:
        raise _AIError('AI 助教套件尚未安裝（pip install anthropic）。')

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = getattr(settings, 'AI_ASSISTANT_MODEL', 'claude-opus-5')
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            output_config={'effort': 'low'},
            messages=[{'role': 'user', 'content': user_message}],
        )
    except anthropic.RateLimitError:
        raise _AIError('AI 助教目前使用量較高，請稍後再試。')
    except anthropic.AuthenticationError:
        raise _AIError('AI 助教金鑰無效，請聯絡管理者。')
    except Exception as exc:  # noqa: BLE001 - 對外一律回傳友善訊息
        raise _AIError(f'AI 助教暫時無法使用（{type(exc).__name__}）。')

    if getattr(response, 'stop_reason', None) == 'refusal':
        raise _AIError('這個問題我無法回答，換個方式問問看？')
    text = ''.join(b.text for b in response.content if getattr(b, 'type', None) == 'text')
    return text.strip()


def _call_gemini(system, user_message):
    try:
        from google import genai
        from google.genai import types
        from google.genai import errors as genai_errors
    except ImportError:
        raise _AIError('AI 助教套件尚未安裝（pip install google-genai）。')

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-3.8-flash')
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=1024,
        # 這是簡短的問答助教，不需要深度推理；關掉思考可以省成本、
        # 也避免思考把整個 token 預算吃完導致沒有輸出文字。
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    response = None
    for attempt in (1, 2):
        try:
            response = client.models.generate_content(model=model, contents=user_message, config=config)
            break
        except genai_errors.APIError as exc:
            code = getattr(exc, 'code', None)
            # 503/429 常是模型暫時忙碌，重試一次就好，不要浪費額度一直重試。
            if code in (429, 503) and attempt == 1:
                time.sleep(1.5)
                continue
            if code == 401:
                raise _AIError('AI 助教金鑰無效，請聯絡管理者。')
            if code == 429:
                raise _AIError('AI 助教目前使用量較高，請稍後再試。')
            if code == 503:
                raise _AIError('AI 服務目前忙碌中，請稍後再試。')
            raise _AIError(f'AI 助教暫時無法使用（{getattr(exc, "message", None) or type(exc).__name__}）。')
        except Exception as exc:  # noqa: BLE001 - 對外一律回傳友善訊息
            raise _AIError(f'AI 助教暫時無法使用（{type(exc).__name__}）。')

    candidates = getattr(response, 'candidates', None) or []
    if candidates and str(getattr(candidates[0], 'finish_reason', '')).upper() in (
        'SAFETY', 'PROHIBITED_CONTENT', 'RECITATION', 'BLOCKLIST',
    ):
        raise _AIError('這個問題我無法回答，換個方式問問看？')

    return (getattr(response, 'text', '') or '').strip()


def _call_model(system, user_message):
    """呼叫目前設定的 AI 後端，回傳純文字回覆。沒有可用後端或呼叫失敗都拋 _AIError。"""
    provider = _active_provider()
    if provider == 'gemini':
        return _call_gemini(system, user_message)
    if provider == 'anthropic':
        return _call_claude(system, user_message)
    raise _AIError('AI 助教尚未啟用（管理者尚未設定 API 金鑰）。')


def answer_course_question(course, question):
    """回傳 {'ok': bool, 'answer'/'error': str}。"""
    if not is_enabled():
        return {'ok': False, 'error': 'AI 助教尚未啟用（管理者尚未設定 API 金鑰）。'}

    question = (question or '').strip()
    if not question:
        return {'ok': False, 'error': '請先輸入問題。'}

    context = build_course_context(course)
    system = (
        f'你是線上課程「{course.title}」的 AI 課程助教。'
        '請「只」根據下面提供的課程資訊，用繁體中文、親切且簡潔地回答學生的問題。'
        '若問題超出課程範圍或提供的資訊不足以回答，請誠實說明並建議學生到課程問答區詢問講師，不要編造內容。\n\n'
        f'=== 課程資訊 ===\n{context}'
    )

    try:
        answer = _call_model(system, question)
    except _AIError as exc:
        return {'ok': False, 'error': str(exc)}
    return {'ok': True, 'answer': answer or '（沒有產生回覆，請再試一次）'}


def get_ai_bot_user():
    """取得（必要時建立）代表 AI 助教回答的系統帳號。"""
    from django.contrib.auth.models import User
    from .models import Profile

    user, created = User.objects.get_or_create(
        username=AI_BOT_USERNAME,
        defaults={'first_name': 'AI 助教', 'is_active': True},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
    return user


def generate_answer_draft(question):
    """針對一則 CourseQuestion 產生 AI 建議回答文字；無法產生時回傳 None（不拋例外）。"""
    if not is_enabled():
        return None

    course = question.course
    context = build_course_context(course)
    system = (
        f'你是線上課程「{course.title}」的 AI 課程助教，負責在課程問答區自動回答學生的提問。'
        '請「只」根據下面提供的課程資訊，用繁體中文、親切且簡潔地回答。'
        '若問題超出課程範圍、涉及個人化判斷（如成績、個別作業批改）或提供的資訊不足以回答，'
        '請誠實說明目前無法確定，並請學生耐心等待講師親自回覆，不要編造內容。\n\n'
        f'=== 課程資訊 ===\n{context}'
    )

    try:
        answer = _call_model(system, question.content)
    except _AIError:
        return None
    return answer or None


def auto_answer_question(question):
    """為學生的提問自動建立一則 AI 回答（CourseAnswer）。成功回傳該筆回答，失敗回傳 None。"""
    answer_text = generate_answer_draft(question)
    if not answer_text:
        return None

    from .models import CourseAnswer

    bot = get_ai_bot_user()
    return CourseAnswer.objects.create(
        question=question,
        user=bot,
        content=answer_text,
        is_ai_generated=True,
    )
