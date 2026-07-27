"""狀態轉換：訂單付款後的生命週期，與課程的審核

這個 module 是「訂單付款後會發生什麼」與「課程什麼時候能上架」的**唯一**答案。
前台 view 與後台 admin 都只透過這裡，因此不可能出現兩套行為。

詞彙定義見專案根目錄 `CONTEXT.md`。三個階段：

    結帳 checkout.py  →  付款 payments.py  →  開通 transitions.fulfill_order
    （算錢、成立待付款訂單）  （金流閘道）        （開課、標券、通知）

對外五個入口，全部具冪等性，重複呼叫不會重複開課、重複退款或重複發通知：

    fulfill_order(order)                    付款成功 → 開通課程
    approve_refund(refund)                  核准退款 → 撤銷存取
    reject_refund(refund)                   拒絕退款
    approve_course(course, reviewer, ...)   審核通過 → 上架
    reject_course(course, reviewer, ...)    審核退回 → 不上架

**退款保留什麼**：撤銷的是「存取權」（Enrollment），不是歷史。學習紀錄
（LearningRecord / LessonProgress）與評價（Review）一律保留 —— 看過就是看過，
講師的評分也不該因為退款而被追溯竄改。
"""
from django.db import transaction
from django.utils import timezone

from .models import (
    CourseAudit,
    CouponUsage,
    Enrollment,
    Notification,
    UserCoupon,
)


# =========================
# 訂單：付款後的生命週期
# =========================

@transaction.atomic
def fulfill_order(order):
    """付款成功後：開通課程、標記優惠券、發通知。

    冪等：訂單已是 paid 就直接返回，不會重複開課或重複發通知。
    """
    if order.status == 'paid':
        return order

    order.status = 'paid'
    order.save()

    for item in order.items.select_related('course').all():
        Enrollment.objects.get_or_create(student=order.user, course=item.course)

    if order.coupon:
        CouponUsage.objects.get_or_create(
            order=order,
            defaults={
                'user': order.user,
                'coupon': order.coupon,
                'discount_amount': order.discount_amount,
            }
        )
        UserCoupon.objects.filter(
            user=order.user, coupon=order.coupon, status='unused'
        ).update(status='used', used_at=timezone.now())

    titles = '、'.join(i.course.title for i in order.items.all())
    Notification.objects.create(
        user=order.user,
        title='購買成功通知',
        content=f'你已完成付款並開通課程：{titles}（實付 NT$ {order.final_price}）。'
    )
    return order


def _refunded_courses(order):
    """這張訂單涵蓋哪些課程。

    以 OrderItem 為準（多課程訂單只有它是完整的）；極舊的訂單可能沒有明細，
    才退回看 Order.course。
    """
    courses = [item.course for item in order.items.select_related('course').all()]
    if not courses and order.course:
        courses = [order.course]
    return courses


@transaction.atomic
def approve_refund(refund):
    """核准退款：撤銷課程存取、回沖付款、更新訂單與退款狀態、發通知。

    保留 LearningRecord / LessonProgress / Review —— 見 module docstring。
    冪等：退款已是 completed 就直接返回。
    """
    if refund.status == 'completed':
        return refund

    order = refund.order

    # 撤銷存取權。學習紀錄與評價不動。
    for course in _refunded_courses(order):
        Enrollment.objects.filter(student=order.user, course=course).delete()

    order.payments.filter(status='paid').update(status='refunded')

    order.status = 'refunded'
    order.save(update_fields=['status'])

    refund.status = 'completed'
    if refund.processed_at is None:
        refund.processed_at = timezone.now()
    refund.save(update_fields=['status', 'processed_at'])

    Notification.objects.create(
        user=refund.user,
        title='退款已通過',
        content=(
            f'訂單 #{order.id} 的退款申請已通過，將退還 NT$ {refund.amount}。'
            f'該訂單的課程存取權已收回。'
        )
    )
    return refund


@transaction.atomic
def reject_refund(refund):
    """拒絕退款：只更新狀態並通知，訂單與課程存取權不變。

    冪等：非 pending 的退款直接返回。
    """
    if refund.status != 'pending':
        return refund

    refund.status = 'rejected'
    refund.processed_at = timezone.now()
    refund.save(update_fields=['status', 'processed_at'])

    Notification.objects.create(
        user=refund.user,
        title='退款未通過',
        content=f'訂單 #{refund.order_id} 的退款申請未通過。'
    )
    return refund


# =========================
# 課程：審核
# =========================

def _latest_audit(course):
    """取最新一筆審核紀錄；從未送審過的課程（例如後台直接建立的）補一筆。"""
    audit = CourseAudit.objects.filter(course=course).order_by('-id').first()
    return audit if audit is not None else CourseAudit(course=course)


@transaction.atomic
def approve_course(course, reviewer, comment=''):
    """審核通過：寫審核紀錄、上架、通知講師。

    上架的唯一路徑 —— 後台的批次上架也走這裡，因此不存在繞過審核的旁路。
    冪等：已通過且已上架時不重發通知。
    """
    audit = _latest_audit(course)
    if audit.pk and audit.status == 'approved' and course.is_published:
        return audit

    audit.status = 'approved'
    audit.reviewer = reviewer
    audit.comment = comment
    audit.reviewed_at = timezone.now()
    audit.save()

    if not course.is_published:
        course.is_published = True
        course.save(update_fields=['is_published'])

    Notification.objects.create(
        user=course.teacher,
        title='課程審核通過',
        content=f'你的課程「{course.title}」已通過審核並上架。'
    )
    return audit


@transaction.atomic
def reject_course(course, reviewer, comment=''):
    """審核退回：寫審核紀錄、確保未上架、通知講師。

    冪等：已退回且已下架時不重發通知。
    """
    audit = _latest_audit(course)
    if audit.pk and audit.status == 'rejected' and not course.is_published:
        return audit

    audit.status = 'rejected'
    audit.reviewer = reviewer
    audit.comment = comment
    audit.reviewed_at = timezone.now()
    audit.save()

    if course.is_published:
        course.is_published = False
        course.save(update_fields=['is_published'])

    Notification.objects.create(
        user=course.teacher,
        title='課程審核未通過',
        content=f'你的課程「{course.title}」未通過審核。原因：{comment or "未提供"}'
    )
    return audit
