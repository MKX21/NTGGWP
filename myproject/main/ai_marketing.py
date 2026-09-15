import json
import logging
import time

from django.conf import settings
from django.utils import timezone

from .ai_assistant import _active_provider

logger = logging.getLogger(__name__)

def _collect_course_data(marketing_request):
    course = marketing_request.course
    teacher = marketing_request.teacher

    chapters = course.chapters.prefetch_related("lessons").order_by("sort_order")
    chapter_list = []
    for ch in chapters:
        lessons = ch.lessons.order_by("sort_order")
        chapter_list.append({
            "title": ch.title,
            "lessons": [ls.title for ls in lessons],
        })

    from main.models import Review, Enrollment
    from django.db.models import Avg, Count
    review_agg = Review.objects.filter(course=course).aggregate(
        avg=Avg("rating"), cnt=Count("id")
    )

    student_count = Enrollment.objects.filter(course=course).count()

    effective_price = course.get_effective_price()

    data = {
        "course_title": course.title,
        "course_description": course.description or "",
        "teacher_name": teacher.username,
        "category": course.category.name if course.category else "未分類",
        "level": course.get_level_display(),
        "original_price": course.price,
        "effective_price": effective_price,
        "is_crowdfunding": course.is_crowdfunding,
        "student_count": student_count,
        "avg_rating": float(review_agg["avg"]) if review_agg["avg"] else None,
        "review_count": review_agg["cnt"],
        "chapters": chapter_list,
        "total_chapters": len(chapter_list),
        "total_lessons": sum(len(ch["lessons"]) for ch in chapter_list),
        "marketing_goal": marketing_request.get_goal_display(),
        "teacher_notes": marketing_request.notes or "（無補充）",
    }

    if course.is_crowdfunding:
        data["funding_goal"] = course.funding_goal
        data["funding_progress"] = course.funding_progress_percent()

    return data

def _build_prompt(course_data):
    system_prompt = (
        "你是一位專業的線上課程行銷企劃師，專精於繁體中文線上教育市場。"
        "你的任務是根據課程資料，產生完整的行銷企劃。"
        "請用繁體中文回覆。不要使用任何表情符號（emoji）。"
        "請嚴格按照指定的 JSON 格式回覆，不要加入任何額外文字或 markdown 標記。"
    )

    chapters_text = ""
    for i, ch in enumerate(course_data["chapters"], 1):
        lessons_text = ", ".join(ch["lessons"]) if ch["lessons"] else "（無單元）"
        chapters_text += f"  第{i}章：{ch['title']}（{lessons_text}）\n"

    user_prompt = f"""請根據以下課程資料，產生完整的行銷企劃。

=== 課程資料 ===
課程名稱：{course_data['course_title']}
課程介紹：{course_data['course_description']}
講師：{course_data['teacher_name']}
分類：{course_data['category']}
難度：{course_data['level']}
原價：NT${course_data['original_price']}
優惠價：NT${course_data['effective_price']}
目前學生數：{course_data['student_count']} 人
平均評分：{course_data['avg_rating'] or '尚無評價'}（{course_data['review_count']} 則評價）
總章節數：{course_data['total_chapters']} 章，{course_data['total_lessons']} 個單元

=== 課程大綱 ===
{chapters_text}
=== 行銷需求 ===
行銷目的：{course_data['marketing_goal']}
教師補充：{course_data['teacher_notes']}

請回覆以下 JSON 格式（純 JSON，不要包含 ```json 標記）：
{{
  "target_audience": "目標受眾分析（150-300字，描述適合的學習者特徵、痛點、需求）",
  "course_selling_points": "課程賣點分析（150-300字，列出3-5個核心賣點）",
  "marketing_strategy": "行銷策略建議（200-400字，包含推廣管道、時間節奏、預算分配建議）",
  "ad_headline": "廣告標題（20字以內，吸引點擊）",
  "ad_copy": "廣告文案（100-200字，適用於 Facebook/Google 廣告）",
  "social_media_copy": "社群貼文（150-300字，適用於 Instagram/Facebook 貼文，含hashtag）",
  "video_script": "短影音腳本（200-400字，30-60秒的影片腳本，標註畫面和旁白）",
  "call_to_action": "行動呼籲（30字以內，例如：立即報名享早鳥優惠）"
}}"""

    return system_prompt, user_prompt

def _call_claude(system_prompt, user_prompt):
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic 套件未安裝")
        return None, "伺服器未安裝 anthropic 套件，請執行 pip install anthropic。"

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=getattr(settings, "AI_ASSISTANT_MODEL", "claude-sonnet-4-6"),
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        reply_text = "".join(
            block.text for block in message.content if hasattr(block, "text")
        )
    except anthropic.AuthenticationError:
        return None, "API 金鑰驗證失敗，請檢查 ANTHROPIC_API_KEY。"
    except anthropic.RateLimitError:
        return None, "API 呼叫頻率超出限制，請稍後再試。"
    except Exception as e:
        logger.error(f"Anthropic API 呼叫失敗: {e}")
        return None, "AI 行銷企劃生成失敗，請稍後再試。"

    return reply_text, None

def _call_gemini(system_prompt, user_prompt):
    try:
        from google import genai
        from google.genai import types
        from google.genai import errors as genai_errors
    except ImportError:
        logger.error("google-genai 套件未安裝")
        return None, "伺服器未安裝 google-genai 套件，請執行 pip install google-genai。"

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model = getattr(settings, "GEMINI_MARKETING_MODEL", "gemini-3.6-flash")
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=8192,
        response_mime_type="application/json",
    )

    response = None
    for attempt in (1, 2):
        try:
            response = client.models.generate_content(
                model=model, contents=user_prompt, config=config
            )
            break
        except genai_errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code in (429, 503) and attempt == 1:
                time.sleep(1.5)
                continue
            if code == 401:
                return None, "API 金鑰驗證失敗，請檢查 GEMINI_API_KEY。"
            if code == 429:
                return None, "API 呼叫頻率超出限制，請稍後再試。"
            if code == 503:
                return None, "AI 服務目前忙碌中，請稍後再試。"
            logger.error(f"Gemini API 呼叫失敗: {exc}")
            return None, "AI 行銷企劃生成失敗，請稍後再試。"
        except Exception as e:
            logger.error(f"Gemini API 呼叫失敗: {e}")
            return None, "AI 行銷企劃生成失敗，請稍後再試。"

    return (getattr(response, "text", "") or ""), None

def generate_marketing_plan(marketing_request):
    provider = _active_provider()
    if provider is None:
        return False, "AI 行銷企劃尚未啟用，請設定 ANTHROPIC_API_KEY 或 GEMINI_API_KEY。"

    try:
        course_data = _collect_course_data(marketing_request)
    except Exception as e:
        logger.error(f"收集課程資料失敗: {e}")
        return False, "收集課程資料時發生錯誤，請稍後再試。"

    system_prompt, user_prompt = _build_prompt(course_data)

    if provider == "gemini":
        reply_text, error = _call_gemini(system_prompt, user_prompt)
    else:
        reply_text, error = _call_claude(system_prompt, user_prompt)
    if error:
        return False, error

    try:
        cleaned = reply_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        plan_data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"AI 回覆 JSON 解析失敗: {e}\n回覆內容: {reply_text[:500]}")
        return False, f"AI 回覆格式解析失敗，請重新生成。"

    required_fields = [
        "target_audience", "course_selling_points", "marketing_strategy",
        "ad_headline", "ad_copy", "social_media_copy",
        "video_script", "call_to_action",
    ]
    for field in required_fields:
        if field not in plan_data or not plan_data[field]:
            plan_data[field] = "（AI 未產生此欄位，請手動補充）"

    return True, plan_data

def create_or_update_plan(marketing_request):
    from main.models import MarketingPlan

    success, result = generate_marketing_plan(marketing_request)

    if not success:
        return False, result, None

    plan_data = result

    plan, created = MarketingPlan.objects.get_or_create(
        marketing_request=marketing_request,
        defaults={"status": "reviewing"},
    )

    plan.target_audience = plan_data["target_audience"]
    plan.course_selling_points = plan_data["course_selling_points"]
    plan.marketing_strategy = plan_data["marketing_strategy"]
    plan.ad_headline = plan_data["ad_headline"]
    plan.ad_copy = plan_data["ad_copy"]
    plan.social_media_copy = plan_data["social_media_copy"]
    plan.video_script = plan_data["video_script"]
    plan.call_to_action = plan_data["call_to_action"]
    plan.status = "reviewing"
    plan.generated_at = timezone.now()
    plan.save()

    marketing_request.status = "processing"
    marketing_request.save(update_fields=["status", "updated_at"])

    action = "建立" if created else "更新"
    return True, f"AI 行銷企劃已{action}，狀態設為「待審核」。", plan
