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

多輪對話：ask_ai / ask_platform_ai 的前端會保留對話歷史，每次送出時附帶
最近的對話紀錄（上限 MAX_HISTORY_TURNS 輪），讓 AI 能延續語境回答追問。
"""
import logging
import time

from django.conf import settings
from django.utils.html import escape as html_escape

AI_BOT_USERNAME = 'ai_assistant'

# 多輪對話：最多保留幾輪歷史（一問一答算一輪）
MAX_HISTORY_TURNS = 5
# 單次輸入上限（字元數），超過截斷以控制 API 成本
MAX_QUESTION_LENGTH = 500

logger = logging.getLogger(__name__)


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
        'label': '如何觀看課程',
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
        'label': '付費方式介紹',
        'question': '平台支援哪些付費方式？',
        'keywords': ['付費', '付款', '怎麼付', '付款方式', '信用卡', '結帳', '怎麼買課', '購買方式', 'ATM', '超商'],
        'answer': (
            '結帳時可選擇以下付款方式：信用卡即時付款、ATM 虛擬帳號轉帳（3 天內匯款）、'
            '超商代碼繳費（7 天內繳費）。課程會依「售價」計價'
            '（募資期間內優先套用早鳥價，其次是折扣價，兩者不疊加），'
            '平台促銷會再疊加在售價上，若有優惠券可於結帳頁輸入折抵碼折抵。'
        ),
    },
    {
        'id': 'refund-policy',
        'label': '退款政策',
        'question': '我可以退款嗎？退款怎麼申請？',
        'keywords': ['退款', '退費', '退錢', '不滿意', '退課', '怎麼退', '退款政策', '可以退嗎'],
        'answer': (
            '平台提供開課後 7 天內不滿意可申請退費的保障。'
            '到「我的課程」找到該課程，點選「申請退款」填寫原因送出即可。'
            '退款需經審核（課程講師或管理員）通過才會生效；'
            '退款成功後會撤銷課程觀看權限，但你的學習紀錄與評價會保留。'
        ),
    },
    {
        'id': 'certificate',
        'label': '如何取得證書',
        'question': '完成課程後可以拿到證書嗎？',
        'keywords': ['證書', '結業', '完成課程', '畢業', '結業證書', '憑證', '完課證明'],
        'answer': (
            '完成課程所有單元後，即可在「我的課程」頁面下載 PDF 結業證書。'
            '證書上會顯示你的帳號名稱、課程名稱、授課講師與完成日期。'
            '每個單元需觀看至少 60% 的影片時長才會被標記為「已完成」。'
        ),
    },
    {
        'id': 'course-missing',
        'label': '課程不見了',
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
        'label': '忘記帳號密碼',
        'question': '我忘記帳號或密碼了怎麼辦？',
        'keywords': ['忘記密碼', '忘記帳號', '密碼忘記', '登入不了', '無法登入', '找回密碼', '重設密碼'],
        'answer': (
            '忘記密碼：請到登入頁點選「忘記密碼」，輸入註冊時使用的 Email 以重設密碼。\n'
            '忘記帳號：帳號通常就是註冊時使用的 Email，若仍無法確認，請聯絡平台管理員協助查詢。'
        ),
    },
    {
        'id': 'progress',
        'label': '學習進度怎麼算',
        'question': '我的學習進度是怎麼計算的？',
        'keywords': ['進度', '學習進度', '完成度', '觀看進度', '看了多少', '學到哪', '百分比'],
        'answer': (
            '每個單元的觀看進度是以「實際看過的秒數」占「影片總長」的比例計算，'
            '快轉跳過的部分不會被計入。當某單元觀看超過 60% 就會標記為「已完成」。'
            '整門課程的進度則是「已完成單元數 / 總單元數」。'
            '你可以在「我的課程」頁面查看每門課的整體完成進度。'
        ),
    },
    {
        'id': 'coupon',
        'label': '優惠券怎麼用',
        'question': '我有優惠券要怎麼使用？',
        'keywords': ['優惠券', '優惠碼', '折扣碼', '折價券', '抵用券', '怎麼用券', '領取優惠'],
        'answer': (
            '進入購物車頁面，可以看到「可領取的優惠券」區塊，點擊即可領取到你的帳戶。'
            '結帳時在優惠碼欄位輸入對應的代碼，系統會自動計算折扣金額。'
            '每張優惠券有使用期限與最低消費門檻，過期或已用完的優惠券無法使用。'
        ),
    },
    {
        'id': 'become-teacher',
        'label': '如何成為講師',
        'question': '我想開課，要怎麼成為講師？',
        'keywords': ['成為講師', '想開課', '當講師', '怎麼教課', '講師申請', '我想教', '開課資格'],
        'answer': (
            '講師身分由平台管理員在後台開通，不是自行註冊或切換的。'
            '如果你有意願成為講師，請透過平台聯絡管理員提出申請，'
            '審核通過後你的帳號就會被授予教師權限，即可在教師專區建立課程。'
            '新課程建立後需經平台審核通過才會正式上架。'
        ),
    },
    {
        'id': 'crowdfunding',
        'label': '什麼是募資課程',
        'question': '募資課程是什麼？跟一般課程有什麼不同？',
        'keywords': ['募資', '集資', '早鳥', '募資課程', '預購', '募資中', '提案'],
        'answer': (
            '募資課程是講師在正式開課前，先公開課程企劃讓學員「預購」支持的模式。'
            '募資期間會有早鳥優惠價，價格通常比正式開課後便宜。'
            '達到募資目標人數後課程確定開設，講師會按進度上傳課程內容。'
            '若未達標，平台會依退款政策處理。已購買的募資課程在正式上架後可直接觀看。'
        ),
    },
    {
        'id': 'playback-speed',
        'label': '可以調整播放速度嗎',
        'question': '看課程影片可以加速或放慢嗎？',
        'keywords': ['播放速度', '倍速', '加速', '放慢', '快轉', '速度調整', '2倍速', '1.5倍'],
        'answer': (
            '可以。影片下方有播放速度控制列，支援 0.5x、0.75x、1x、1.25x、1.5x、2x 六段速度。'
            '另外也支援鍵盤快捷鍵：空白鍵暫停／播放、左右箭頭快轉 5 秒、上下箭頭調整音量、'
            'M 鍵靜音、F 鍵全螢幕。'
        ),
    },
    {
        'id': 'bundle',
        'label': '合購組合是什麼',
        'question': '什麼是合購組合？怎麼買比較划算？',
        'keywords': ['合購', '組合', '套餐', '一起買', '組合價', '打包', '合購組合'],
        'answer': (
            '合購組合是平台或講師將多門相關課程打包成一個優惠套餐，'
            '整組購買的價格會比個別購買便宜。在課程頁面或購物車中，'
            '如果有可用的合購組合會自動顯示。把組合內所有課程都加入購物車，'
            '結帳時會自動套用組合優惠價。'
        ),
    },
    {
        'id': 'account-settings',
        'label': '修改個人資料',
        'question': '要怎麼修改我的名稱、頭貼或 Email？',
        'keywords': ['修改資料', '改名', '頭貼', '大頭貼', '個人資料', '修改密碼', '改密碼', '帳號設定'],
        'answer': (
            '登入後點右上角頭像，選擇「會員資料」即可進入個人資料頁面。'
            '在這裡你可以修改顯示名稱、自我介紹、大頭貼等資訊。'
            '如需修改密碼，請到登入頁點選「忘記密碼」透過 Email 重設。'
        ),
    },
    {
        'id': 'order-status',
        'label': '查詢訂單狀態',
        'question': '要怎麼查看我的訂單狀態？',
        'keywords': ['訂單', '訂單狀態', '付款狀態', '待付款', '訂單查詢', '買了沒', '有沒有成功'],
        'answer': (
            '登入後到「我的課程」頁面可以看到所有已購買的課程。'
            '若訂單狀態為「待付款」，代表尚未完成付款，'
            '可到通知列表查看付款資訊（ATM 帳號或超商代碼），於期限內完成繳費即可開通課程。'
        ),
    },
    {
        'id': 'contact-teacher',
        'label': '怎麼聯繫講師',
        'question': '有問題想問講師要怎麼聯繫？',
        'keywords': ['聯繫講師', '問講師', '聯絡老師', '怎麼問', '問問題', '提問'],
        'answer': (
            '購買課程後，可以在課程頁面的「問與答」區塊直接發問，'
            '講師會在問答區回覆。平台也有 AI 課程助教可以即時回答課程內容相關的問題。'
            '如需要私訊講師，可以到講師的個人頁面查看是否有提供社群聯絡方式。'
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


def build_course_faq(course):
    """根據課程的實際資料，動態產生該課程專屬的快速問答按鈕。"""
    from .models import CourseLesson, Enrollment, Review
    from django.db.models import Avg, Sum

    faqs = []

    # 課程時長
    total_minutes = CourseLesson.objects.filter(
        chapter__course=course
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0
    lesson_count = CourseLesson.objects.filter(chapter__course=course).count()
    if lesson_count > 0:
        faqs.append({
            'id': f'course-info-{course.id}',
            'label': '課程內容有多少？',
            'question': '這門課有多少內容？',
            'answer': (
                f'「{course.title}」共有 {course.chapters.count()} 個章節、'
                f'{lesson_count} 個單元，總時長約 {total_minutes} 分鐘。'
            ),
        })

    # 學生數與評價
    student_count = Enrollment.objects.filter(course=course).count()
    avg = Review.objects.filter(course=course).aggregate(a=Avg('rating'))['a']
    review_count = Review.objects.filter(course=course).count()
    if student_count > 0 or review_count > 0:
        parts = []
        if student_count > 0:
            parts.append(f'目前已有 {student_count} 位學生購買')
        if review_count > 0 and avg:
            parts.append(f'平均評分 {avg:.1f} 星（{review_count} 則評價）')
        faqs.append({
            'id': f'course-stats-{course.id}',
            'label': '有多少人上過？',
            'question': '這門課有多少學生？評價如何？',
            'answer': '，'.join(parts) + '。',
        })

    # 價格
    effective = course.get_effective_price()
    if effective < course.price:
        faqs.append({
            'id': f'course-price-{course.id}',
            'label': '目前有優惠嗎？',
            'question': '這門課現在有折扣嗎？',
            'answer': (
                f'「{course.title}」原價 NT$ {course.price}，'
                f'目前售價 NT$ {effective}，現省 NT$ {course.price - effective}！'
            ),
        })

    return faqs


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
    from .models import CourseLesson, Enrollment, Review
    from django.db.models import Avg, Sum

    lines = [f'課程名稱：{course.title}']
    try:
        lines.append(f'講師：{course.teacher.profile.display_name}')
        if course.teacher.profile.bio:
            lines.append(f'講師簡介：{course.teacher.profile.bio}')
    except Exception:
        pass
    if course.category:
        lines.append(f'分類：{course.category.name}')
    lines.append(f'難度：{course.get_level_display()}')

    # 價格資訊
    effective = course.get_effective_price()
    if effective < course.price:
        lines.append(f'價格：原價 NT${course.price}，目前售價 NT${effective}')
    else:
        lines.append(f'價格：NT${course.price}')

    # 統計資訊（讓 AI 能回答「有多少人上過」等問題）
    student_count = Enrollment.objects.filter(course=course).count()
    lines.append(f'已購買學生數：{student_count} 人')

    avg = Review.objects.filter(course=course).aggregate(a=Avg('rating'))['a']
    review_count = Review.objects.filter(course=course).count()
    if review_count > 0 and avg:
        lines.append(f'平均評分：{avg:.1f} 星（{review_count} 則評價）')

    total_minutes = CourseLesson.objects.filter(
        chapter__course=course
    ).aggregate(total=Sum('duration_minutes'))['total'] or 0
    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    lines.append(f'課程規模：{course.chapters.count()} 章、{total_lessons} 個單元、共 {total_minutes} 分鐘')

    lines.append(f'課程簡介：{course.description}')

    lines.append('課程大綱：')
    for chapter in course.chapters.prefetch_related('lessons').all():
        lines.append(f'  章節：{chapter.title}')
        for lesson in chapter.lessons.all():
            dur = f'（{lesson.duration_minutes} 分鐘）' if lesson.duration_minutes else ''
            preview = '【免費試看】' if lesson.is_free_preview else ''
            lines.append(f'    - 單元：{lesson.title} {dur}{preview}')
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
        '退款：平台提供開課後 7 天內不滿意可申請退費的保障。已付款的訂單可以在「我的課程」頁面提出申請，'
        '需經審核（課程講師或管理員）通過才會生效；退款會撤銷購課存取權，但學習紀錄與已寫的課程評價會保留。'
    )
    lines.append(
        '證書：完成課程所有單元後，可以在「我的課程」下載 PDF 結業證書。'
        '每個單元需觀看至少 60% 的影片時長才會被標記為「已完成」。'
    )
    lines.append(
        '課程上架與可見性：未上架的課程只有課程講師本人、平台管理員、以及已購買過的學生看得到，'
        '其餘使用者看不到、也無法購買。'
    )
    lines.append(
        '角色：學生（購課、觀看、評價、提問）、講師（開課、管理課程內容、回答提問）、'
        '管理員（審核課程與退款、平台分析）。講師身分是由平台管理員在後台開通，不是自行申請切換。'
    )
    lines.append(
        '付款方式：信用卡即時付款、ATM 虛擬帳號轉帳（3 天期限）、超商代碼繳費（7 天期限）。'
    )

    lines.append('')
    lines.append('=== 目前上架中的課程（可用於推薦） ===')
    courses = Course.objects.filter(is_published=True).select_related('category', 'teacher')
    if not courses:
        lines.append('（目前沒有上架中的課程）')
    for c in courses:
        desc = (c.description or '').strip().replace('\n', ' ')
        if len(desc) > 60:
            desc = desc[:60] + '...'
        cat = c.category.name if c.category else '未分類'
        try:
            price = int(c.get_effective_price())
            price_text = f'NT${price}'
        except Exception:
            price_text = '（價格未知）'
        lines.append(f'- 「{c.title}」（分類：{cat}，{price_text}，難度：{c.get_level_display()}）：{desc}')
    return '\n'.join(lines)


def _truncate_question(question):
    """截斷過長的問題以控制 API token 成本。"""
    question = (question or '').strip()
    if len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH] + '...'
    return question


def _build_messages(question, history=None):
    """把對話歷史轉換成 API 需要的 messages 格式。

    history 格式：[{'role': 'user'|'ai', 'text': str}, ...]
    只保留最近 MAX_HISTORY_TURNS 輪（一問一答算一輪）。
    """
    messages = []

    if history:
        # 取最近 N 輪（每輪 = 一個 user + 一個 ai）
        recent = history[-(MAX_HISTORY_TURNS * 2):]
        for entry in recent:
            role = 'user' if entry.get('role') == 'user' else 'assistant'
            text = (entry.get('text') or '').strip()
            if text:
                # 安全截斷歷史訊息
                if len(text) > MAX_QUESTION_LENGTH:
                    text = text[:MAX_QUESTION_LENGTH] + '...'
                messages.append({'role': role, 'content': text})

    messages.append({'role': 'user', 'content': question})
    return messages


def answer_platform_question(question, history=None):
    """回傳 {'ok': bool, 'answer'/'error': str, 'suggestions': list}。
    首頁平台助手：FAQ + 課程推薦，不綁定單一課程。

    history: 前端送來的對話歷史，用於多輪對話。
    """
    if not is_enabled():
        return {'ok': False, 'error': 'AI 助教尚未啟用（管理者尚未設定 API 金鑰）。'}

    question = _truncate_question(question)
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
        '若問題超出平台範圍或提供的資訊不足以回答，請誠實說明，不要編造內容。'
        '\n\n在回覆的最後一行，請用 ||| 分隔符號附上 2~3 個建議追問，格式為：'
        '|||建議問題1|||建議問題2|||建議問題3'
        '（例如：|||有沒有適合初學者的課程？|||怎麼申請退款？|||優惠券去哪裡領？）'
        '\n\n'
        f'{context}'
    )

    try:
        messages = _build_messages(question, history)
        answer = _call_model(system, messages)
    except _AIError as exc:
        return {'ok': False, 'error': str(exc)}

    if not answer:
        return {'ok': True, 'answer': '（没有產生回覆，請再試一次）', 'suggestions': []}

    # 解析建議追問
    answer_text, suggestions = _parse_suggestions(answer)
    return {'ok': True, 'answer': answer_text, 'suggestions': suggestions}


def answer_course_question(course, question, history=None):
    """回傳 {'ok': bool, 'answer'/'error': str, 'suggestions': list}。

    history: 前端送來的對話歷史，用於多輪對話。
    """
    if not is_enabled():
        return {'ok': False, 'error': 'AI 助教尚未啟用（管理者尚未設定 API 金鑰）。'}

    question = _truncate_question(question)
    if not question:
        return {'ok': False, 'error': '請先輸入問題。'}

    context = build_course_context(course)
    system = (
        f'你是線上課程「{course.title}」的 AI 課程助教。'
        '請「只」根據下面提供的課程資訊，用繁體中文、親切且簡潔地回答學生的問題。'
        '若問題超出課程範圍或提供的資訊不足以回答，請誠實說明並建議學生到課程問答區詢問講師，不要編造內容。'
        '\n\n在回覆的最後一行，請用 ||| 分隔符號附上 2~3 個建議追問，格式為：'
        '|||建議問題1|||建議問題2|||建議問題3'
        '（例如：|||這門課適合完全沒基礎的人嗎？|||有沒有免費試看的單元？|||課程有提供教材下載嗎？）'
        '\n\n'
        f'=== 課程資訊 ===\n{context}'
    )

    try:
        messages = _build_messages(question, history)
        answer = _call_model(system, messages)
    except _AIError as exc:
        return {'ok': False, 'error': str(exc)}

    if not answer:
        return {'ok': True, 'answer': '（没有產生回覆，請再試一次）', 'suggestions': []}

    answer_text, suggestions = _parse_suggestions(answer)
    return {'ok': True, 'answer': answer_text, 'suggestions': suggestions}


def _parse_suggestions(text):
    """從 AI 回覆中解析建議追問。

    回傳 (answer_text, suggestions_list)。
    """
    if '|||' not in text:
        return text.strip(), []

    parts = text.split('|||')
    answer_text = parts[0].strip()
    suggestions = [s.strip() for s in parts[1:] if s.strip()]
    # 最多取 3 個建議
    return answer_text, suggestions[:3]


def _call_claude(system, messages):
    """呼叫 Claude API。messages 是完整的對話歷史（含最新問題）。"""
    try:
        import anthropic
    except ImportError:
        raise _AIError('AI 助教套件尚未安裝（pip install anthropic）。')

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = getattr(settings, 'AI_ASSISTANT_MODEL', 'claude-opus-5')

        # 把 messages 轉成 Anthropic 格式
        api_messages = []
        for msg in messages:
            api_messages.append({
                'role': msg['role'],
                'content': msg['content'],
            })

        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=api_messages,
        )
    except anthropic.RateLimitError:
        raise _AIError('AI 助教目前使用量較高，請稍後再試。')
    except anthropic.AuthenticationError:
        raise _AIError('AI 助教金鑰無效，請聯絡管理者。')
    except Exception as exc:  # noqa: BLE001 - 對外一律回傳友善訊息
        logger.warning('Claude API error: %s', exc)
        raise _AIError(f'AI 助教暫時無法使用（{type(exc).__name__}）。')

    if getattr(response, 'stop_reason', None) == 'refusal':
        raise _AIError('這個問題我無法回答，換個方式問問看？')
    text = ''.join(b.text for b in response.content if getattr(b, 'type', None) == 'text')
    return text.strip()


def _call_gemini(system, messages):
    """呼叫 Gemini API。messages 是完整的對話歷史（含最新問題）。"""
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

    # 將多輪歷史轉成 Gemini 的 contents 格式
    contents = []
    for msg in messages:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg['content'])],
        ))

    response = None
    for attempt in (1, 2):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
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
            logger.warning('Gemini API error: %s', exc)
            raise _AIError(f'AI 助教暫時無法使用（{type(exc).__name__}）。')

    candidates = getattr(response, 'candidates', None) or []
    if candidates and str(getattr(candidates[0], 'finish_reason', '')).upper() in (
        'SAFETY', 'PROHIBITED_CONTENT', 'RECITATION', 'BLOCKLIST',
    ):
        raise _AIError('這個問題我無法回答，換個方式問問看？')

    return (getattr(response, 'text', '') or '').strip()


def _call_model(system, messages):
    """呼叫目前設定的 AI 後端，回傳純文字回覆。

    messages: [{'role': 'user'|'assistant', 'content': str}, ...]
    沒有可用後端或呼叫失敗都拋 _AIError。
    """
    provider = _active_provider()
    if provider == 'gemini':
        return _call_gemini(system, messages)
    if provider == 'anthropic':
        return _call_claude(system, messages)
    raise _AIError('AI 助教尚未啟用（管理者尚未設定 API 金鑰）。')


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
        messages = [{'role': 'user', 'content': question.content}]
        answer = _call_model(system, messages)
    except _AIError:
        return None
    # auto_answer 不需要建議追問，直接去掉
    if answer and '|||' in answer:
        answer = answer.split('|||')[0].strip()
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
