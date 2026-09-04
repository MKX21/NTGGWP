from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from main.models import (
    Profile,
    CourseCategory,
    Course,
    CourseChapter,
    CourseLesson,
    Enrollment,
    LearningRecord,
    Coupon,
    UserCoupon,
    Promotion,
    Cart,
    CartItem,
    Order,
    OrderItem,
    CouponUsage,
    Payment,
    Favorite,
    Review,
    Notification,
    CourseQuestion,
    CourseAnswer,
    CourseAudit,
)


def create_user(username, email, password, role=None, is_superuser=False):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": is_superuser,
            "is_superuser": is_superuser,
        }
    )

    if created:
        user.set_password(password)
        user.save()
    else:
        user.email = email
        if is_superuser:
            user.is_staff = True
            user.is_superuser = True
        user.save()

    if role:
        Profile.objects.get_or_create(
            user=user,
            defaults={"role": role}
        )

    return user


print("開始建立測試資料...")

# =========================
# 1. 建立使用者
# =========================

admin = create_user(
    username="admin_demo",
    email="admin@example.com",
    password="Admin12345",
    is_superuser=True
)

teacher1 = create_user(
    username="teacher_python",
    email="teacher_python@example.com",
    password="Teacher12345",
    role="teacher"
)

teacher2 = create_user(
    username="teacher_design",
    email="teacher_design@example.com",
    password="Teacher12345",
    role="teacher"
)

student1 = create_user(
    username="student_amy",
    email="amy@example.com",
    password="Student12345",
    role="student"
)

student2 = create_user(
    username="student_ben",
    email="ben@example.com",
    password="Student12345",
    role="student"
)

student3 = create_user(
    username="student_cindy",
    email="cindy@example.com",
    password="Student12345",
    role="student"
)

# =========================
# 2. 課程分類
# =========================

cat_programming, _ = CourseCategory.objects.get_or_create(
    name="程式設計",
    defaults={"description": "Python、Django、網頁開發與資料庫相關課程"}
)

cat_design, _ = CourseCategory.objects.get_or_create(
    name="設計與行銷",
    defaults={"description": "UI/UX、品牌設計、社群行銷與內容經營"}
)

cat_business, _ = CourseCategory.objects.get_or_create(
    name="商業管理",
    defaults={"description": "創業、營運、資料分析與商業決策"}
)

# =========================
# 3. 課程
# =========================

course_data = [
    {
        "title": "Python Django 線上課程平台實作",
        "teacher": teacher1,
        "category": cat_programming,
        "price": 1800,
        "level": "intermediate",
        "description": "從 Django 基礎開始，實作會員登入、課程管理、購課流程與 MySQL 資料庫串接。",
    },
    {
        "title": "MySQL 資料庫設計與 ERD 實戰",
        "teacher": teacher1,
        "category": cat_programming,
        "price": 1500,
        "level": "beginner",
        "description": "學習資料表設計、主外鍵關聯、訂單與優惠券資料庫架構，並建立完整 ERD。",
    },
    {
        "title": "Power BI 商業數據分析入門",
        "teacher": teacher2,
        "category": cat_business,
        "price": 2000,
        "level": "beginner",
        "description": "使用 Power BI 分析課程平台資料，製作營收、購課、學習時數與優惠券儀表板。",
    },
    {
        "title": "UI/UX 介面設計與平台首頁規劃",
        "teacher": teacher2,
        "category": cat_design,
        "price": 1200,
        "level": "beginner",
        "description": "學習網站首頁、課程卡片、使用者流程與平台視覺設計，提升系統展示完整度。",
    },
]

courses = []

for item in course_data:
    course, created = Course.objects.get_or_create(
        title=item["title"],
        defaults={
            "teacher": item["teacher"],
            "category": item["category"],
            "price": item["price"],
            "level": item["level"],
            "description": item["description"],
            "is_published": True,
        }
    )

    if not created:
        course.teacher = item["teacher"]
        course.category = item["category"]
        course.price = item["price"]
        course.level = item["level"]
        course.description = item["description"]
        course.is_published = True
        course.save()

    courses.append(course)

# =========================
# 4. 課程章節與單元
# =========================

for course in courses:
    chapter1, _ = CourseChapter.objects.get_or_create(
        course=course,
        title="第一章：課程導入",
        defaults={
            "description": "介紹課程目標、學習方式與基礎概念。",
            "sort_order": 1,
        }
    )

    chapter2, _ = CourseChapter.objects.get_or_create(
        course=course,
        title="第二章：核心實作",
        defaults={
            "description": "進入主要功能實作與案例操作。",
            "sort_order": 2,
        }
    )

    CourseLesson.objects.get_or_create(
        chapter=chapter1,
        title="1-1 課程介紹與學習目標",
        defaults={
            "content": "本單元說明課程內容、平台功能與學習成果。",
            "video_url": "https://example.com/video/intro",
            "duration_minutes": 15,
            "sort_order": 1,
            "is_free_preview": True,
        }
    )

    CourseLesson.objects.get_or_create(
        chapter=chapter1,
        title="1-2 開發環境與工具介紹",
        defaults={
            "content": "介紹 VS Code、MySQL、Django、Power BI 等工具。",
            "video_url": "https://example.com/video/setup",
            "duration_minutes": 20,
            "sort_order": 2,
            "is_free_preview": False,
        }
    )

    CourseLesson.objects.get_or_create(
        chapter=chapter2,
        title="2-1 核心功能設計",
        defaults={
            "content": "說明會員、課程、訂單、優惠券與學習紀錄的設計。",
            "video_url": "https://example.com/video/core",
            "duration_minutes": 35,
            "sort_order": 1,
            "is_free_preview": False,
        }
    )

    CourseLesson.objects.get_or_create(
        chapter=chapter2,
        title="2-2 資料庫與報表分析",
        defaults={
            "content": "說明 MySQL 資料表與 Power BI 報表的串接方式。",
            "video_url": "https://example.com/video/database",
            "duration_minutes": 40,
            "sort_order": 2,
            "is_free_preview": False,
        }
    )

# =========================
# 5. 優惠券與促銷活動
# =========================

now = timezone.now()

coupon1, _ = Coupon.objects.get_or_create(
    code="NEW100",
    defaults={
        "name": "新會員折扣",
        "discount_type": "amount",
        "discount_value": 100,
        "min_spend": 500,
        "start_date": now - timedelta(days=1),
        "end_date": now + timedelta(days=60),
        "usage_limit": 0,
        "is_active": True,
    }
)

coupon2, _ = Coupon.objects.get_or_create(
    code="SALE20",
    defaults={
        "name": "限時八折優惠",
        "discount_type": "percent",
        "discount_value": 20,
        "min_spend": 1000,
        "start_date": now - timedelta(days=1),
        "end_date": now + timedelta(days=30),
        "usage_limit": 100,
        "is_active": True,
    }
)

promotion, _ = Promotion.objects.get_or_create(
    name="期末專題優惠活動",
    defaults={
        "description": "為專題展示建立的測試促銷活動。",
        "discount_type": "percent",
        "discount_value": 15,
        "start_date": now - timedelta(days=1),
        "end_date": now + timedelta(days=30),
        "is_active": True,
    }
)

promotion.courses.set(courses)

for student in [student1, student2, student3]:
    UserCoupon.objects.get_or_create(
        user=student,
        coupon=coupon1,
        defaults={"status": "unused"}
    )

# =========================
# 6. 購物車
# =========================

cart1, _ = Cart.objects.get_or_create(user=student1)
CartItem.objects.get_or_create(cart=cart1, course=courses[1])

cart2, _ = Cart.objects.get_or_create(user=student2)
CartItem.objects.get_or_create(cart=cart2, course=courses[2])

# =========================
# 7. 建立訂單、購課紀錄、付款紀錄
# =========================

purchase_plan = [
    (student1, courses[0], coupon1),
    (student1, courses[2], None),
    (student2, courses[0], coupon2),
    (student2, courses[1], None),
    (student3, courses[3], coupon1),
]

for student, course, coupon in purchase_plan:
    original_price = course.price
    discount_amount = coupon.calculate_discount(original_price) if coupon else 0
    final_price = original_price - discount_amount

    order, created = Order.objects.get_or_create(
        user=student,
        course=course,
        defaults={
            "coupon": coupon,
            "original_price": original_price,
            "discount_amount": discount_amount,
            "final_price": final_price,
            "status": "paid",
        }
    )

    if created:
        OrderItem.objects.get_or_create(
            order=order,
            course=course,
            defaults={"price": original_price}
        )

        Payment.objects.get_or_create(
            order=order,
            defaults={
                "method": "mock",
                "amount": final_price,
                "status": "paid",
                "transaction_no": f"MOCK-{order.id:05d}",
                "paid_at": now,
            }
        )

        if coupon:
            CouponUsage.objects.get_or_create(
                order=order,
                defaults={
                    "user": student,
                    "coupon": coupon,
                    "discount_amount": discount_amount,
                }
            )

    Enrollment.objects.get_or_create(
        student=student,
        course=course
    )

# =========================
# 8. 學習紀錄
# =========================

for student in [student1, student2, student3]:
    enrollments = Enrollment.objects.filter(student=student)

    for enrollment in enrollments:
        course = enrollment.course
        lessons = CourseLesson.objects.filter(chapter__course=course).order_by("chapter__sort_order", "sort_order")

        for lesson in lessons[:2]:
            LearningRecord.objects.get_or_create(
                user=student,
                course=course,
                lesson=lesson,
                defaults={
                    "minutes": lesson.duration_minutes if lesson.duration_minutes > 0 else 30,
                }
            )

# =========================
# 9. 收藏與評價
# =========================

Favorite.objects.get_or_create(user=student1, course=courses[1])
Favorite.objects.get_or_create(user=student2, course=courses[2])
Favorite.objects.get_or_create(user=student3, course=courses[0])

Review.objects.get_or_create(
    user=student1,
    course=courses[0],
    defaults={
        "rating": 5,
        "comment": "課程內容完整，對專題實作很有幫助。",
    }
)

Review.objects.get_or_create(
    user=student2,
    course=courses[0],
    defaults={
        "rating": 4,
        "comment": "可以快速了解 Django 和資料庫串接。",
    }
)

Review.objects.get_or_create(
    user=student3,
    course=courses[3],
    defaults={
        "rating": 5,
        "comment": "首頁設計和使用者流程講得很清楚。",
    }
)

# =========================
# 10. 通知、問答、審核
# =========================

for student in [student1, student2, student3]:
    Notification.objects.get_or_create(
        user=student,
        title="歡迎加入 Course Platform",
        defaults={
            "content": "你已成功註冊平台，可以開始瀏覽與購買課程。",
            "is_read": False,
        }
    )

question, _ = CourseQuestion.objects.get_or_create(
    user=student1,
    course=courses[0],
    title="Django 和 MySQL 的資料表是怎麼連動的？",
    defaults={
        "content": "我想了解 Django models.py 和 MySQL 資料表之間的關係。",
    }
)

CourseAnswer.objects.get_or_create(
    question=question,
    user=teacher1,
    defaults={
        "content": "Django 會透過 models.py 定義資料結構，再透過 migration 建立 MySQL 資料表。",
    }
)

for course in courses:
    CourseAudit.objects.get_or_create(
        course=course,
        defaults={
            "reviewer": admin,
            "status": "approved",
            "comment": "測試資料：課程已審核通過。",
            "reviewed_at": now,
        }
    )

print("測試資料建立完成！")
print("")
print("可登入帳號：")
print("管理員：admin_demo / Admin12345")
print("老師：teacher_python / Teacher12345")
print("老師：teacher_design / Teacher12345")
print("學生：student_amy / Student12345")
print("學生：student_ben / Student12345")
print("學生：student_cindy / Student12345")
print("")
print("優惠碼：NEW100、SALE20")