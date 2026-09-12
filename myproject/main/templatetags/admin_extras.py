from django import template
from django.db.models import Sum
from django.urls import reverse

from main.models import (
    Course, Enrollment, Order, CourseAudit, Refund,
)

register = template.Library()


@register.simple_tag
def platform_stats():
    """後台首頁營運數據卡片資料（可點擊跳到對應清單）。"""
    total_courses = Course.objects.count()
    published = Course.objects.filter(is_published=True).count()
    students = Enrollment.objects.values('student').distinct().count()
    paid_orders = Order.objects.filter(status='paid').count()
    revenue = Order.objects.filter(status='paid').aggregate(s=Sum('final_price'))['s'] or 0
    pending_audits = CourseAudit.objects.filter(status='pending').count()
    pending_refunds = Refund.objects.filter(status='pending').count()

    order_paid_url = reverse('admin:main_order_changelist') + '?status__exact=paid'

    return [
        {'label': '總營收', 'value': f'NT$ {revenue:,}', 'icon': '💰', 'accent': '#4f46e5',
         'url': order_paid_url},
        {'label': '已付款訂單', 'value': paid_orders, 'icon': '🧾', 'accent': '#7c3aed',
         'url': order_paid_url},
        {'label': '學生人次', 'value': students, 'icon': '👥', 'accent': '#0ea5e9',
         'url': reverse('admin:main_enrollment_changelist')},
        {'label': '上架課程', 'value': f'{published} / {total_courses}', 'icon': '📚', 'accent': '#10b981',
         'url': reverse('admin:main_course_changelist') + '?is_published__exact=1'},
        {'label': '待審核課程', 'value': pending_audits, 'icon': '📝', 'accent': '#f59e0b',
         'alert': pending_audits > 0,
         'url': reverse('admin:main_courseaudit_changelist') + '?status__exact=pending'},
        {'label': '待處理退款', 'value': pending_refunds, 'icon': '↩️', 'accent': '#ef4444',
         'alert': pending_refunds > 0,
         'url': reverse('admin:main_refund_changelist') + '?status__exact=pending'},
    ]
