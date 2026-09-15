from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import (
    CourseAudit,
    CouponUsage,
    Enrollment,
    Notification,
    RevenueRecord,
    UserCoupon,
)

@transaction.atomic
def fulfill_order(order):
    if order.status == 'paid':
        return order

    order.status = 'paid'
    order.save()

    for item in order.items.select_related('course').all():
        Enrollment.objects.get_or_create(student=order.user, course=item.course)
        RevenueRecord.create_for_order_item(item)

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
    courses = [item.course for item in order.items.select_related('course').all()]
    if not courses and order.course:
        courses = [order.course]
    return courses

@transaction.atomic
def approve_refund(refund):
    if refund.status == 'completed':
        return refund

    order = refund.order

    for course in _refunded_courses(order):
        Enrollment.objects.filter(student=order.user, course=course).delete()

    order.payments.filter(status__in=['paid', 'pending']).update(status='refunded')

    order.revenue_records.filter(status='confirmed').update(
        status='reversed', reversed_at=timezone.now()
    )

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

def _latest_audit(course):
    audit = CourseAudit.objects.filter(course=course).order_by('-id').first()
    return audit if audit is not None else CourseAudit(course=course)

@transaction.atomic
def approve_course(course, reviewer, comment=''):
    audit = _latest_audit(course)
    if audit.pk and audit.status == 'approved' and course.is_published:
        return audit

    audit.status = 'approved'
    audit.reviewer = reviewer
    audit.comment = comment
    audit.reviewed_at = timezone.now()
    audit.save()

    newly_published = not course.is_published
    if newly_published:
        course.is_published = True
        course.save(update_fields=['is_published'])

    Notification.objects.create(
        user=course.teacher,
        title='課程審核通過',
        content=f'你的課程「{course.title}」已通過審核並上架。'
    )

    if newly_published:
        from .notifications import notify_followers
        notify_followers(
            course.teacher,
            '追蹤講師有新課程上架',
            f'{course.teacher.profile.display_name}老師發布了新課程「{course.title}」，快來看看！'
        )
    return audit

@transaction.atomic
def reject_course(course, reviewer, comment=''):
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

def _notify_withdrawal(withdrawal, title, content):
    Notification.objects.create(user=withdrawal.teacher, title=title, content=content)

    if withdrawal.teacher.email:
        send_mail(
            subject=f'[EduFlow] {title}',
            message=content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[withdrawal.teacher.email],
            fail_silently=True,
        )

@transaction.atomic
def complete_withdrawal(withdrawal, note=''):
    if withdrawal.status == 'completed':
        return withdrawal

    withdrawal.status = 'completed'
    withdrawal.processed_at = timezone.now()
    if note:
        withdrawal.note = note
    withdrawal.save(update_fields=['status', 'processed_at', 'note'])

    _notify_withdrawal(
        withdrawal,
        title='提領申請已完成',
        content=f'你申請提領的 NT$ {withdrawal.amount} 已撥款完成。'
    )
    return withdrawal

@transaction.atomic
def reject_withdrawal(withdrawal, note=''):
    if withdrawal.status != 'pending':
        return withdrawal

    withdrawal.status = 'rejected'
    withdrawal.processed_at = timezone.now()
    if note:
        withdrawal.note = note
    withdrawal.save(update_fields=['status', 'processed_at', 'note'])

    _notify_withdrawal(
        withdrawal,
        title='提領申請未通過',
        content=f'你申請提領的 NT$ {withdrawal.amount} 未通過。原因：{note or "未提供"}'
    )
    return withdrawal
