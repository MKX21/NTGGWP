from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Profile,
    CourseCategory,
    Course,
    CourseChapter,
    CourseLesson,
    Enrollment,
    LearningRecord,
    LessonProgress,
    Coupon,
    UserCoupon,
    Promotion,
    Cart,
    CartItem,
    Order,
    OrderItem,
    CouponUsage,
    Payment,
    Refund,
    Favorite,
    Review,
    Notification,
    CourseQuestion,
    CourseAnswer,
    CourseAudit,
    TeacherBankAccount,
    WithdrawalRequest,
)

# ===== 後台品牌 =====
admin.site.site_header = "購課平台・營運管理後台"
admin.site.site_title = "課程平台後台"
admin.site.index_title = "營運管理總覽"
admin.site.index_template = "admin/custom_index.html"


# ===== 共用彩色標籤 =====
def _badge(text, fg, bg):
    return format_html(
        '<span style="padding:3px 10px;border-radius:999px;font-size:12px;'
        'font-weight:700;color:{};background:{};white-space:nowrap;">{}</span>',
        fg, bg, text,
    )


STATUS_COLORS = {
    # 訂單
    'pending': ('#92400e', '#fef3c7'),
    'paid': ('#166534', '#dcfce7'),
    'cancelled': ('#475569', '#e2e8f0'),
    'refunded': ('#991b1b', '#fee2e2'),
    # 付款
    'failed': ('#991b1b', '#fee2e2'),
    # 退款 / 審核
    'approved': ('#166534', '#dcfce7'),
    'rejected': ('#991b1b', '#fee2e2'),
    'completed': ('#166534', '#dcfce7'),
    # 券
    'unused': ('#166534', '#dcfce7'),
    'used': ('#475569', '#e2e8f0'),
    'expired': ('#991b1b', '#fee2e2'),
    '已過期': ('#991b1b', '#fee2e2'),
    '使用中': ('#166534', '#dcfce7'),
    '未開始': ('#92400e', '#fef3c7'),
    '已停用': ('#475569', '#e2e8f0'),
    '已用完': ('#475569', '#e2e8f0'),
}


def status_badge(value, label=None):
    fg, bg = STATUS_COLORS.get(value, ('#334155', '#e2e8f0'))
    return _badge(label or value, fg, bg)


# ===== Inlines =====
class CourseChapterInline(admin.TabularInline):
    model = CourseChapter
    extra = 1
    fields = ('sort_order', 'title', 'description')
    ordering = ('sort_order',)


class CourseLessonInline(admin.TabularInline):
    model = CourseLesson
    extra = 1
    fields = ('sort_order', 'title', 'duration_minutes', 'is_free_preview', 'video_file', 'video_url')
    ordering = ('sort_order',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ('course',)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ('method', 'amount', 'status', 'transaction_no', 'paid_at')
    readonly_fields = ('transaction_no',)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ('course',)


class CourseAnswerInline(admin.StackedInline):
    model = CourseAnswer
    extra = 1
    autocomplete_fields = ('user',)


# ===== 會員 =====
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_badge', 'is_teacher', 'oauth_badge')
    list_editable = ('is_teacher',)
    search_fields = ('user__username', 'user__email')
    list_filter = ('role', 'is_teacher')
    actions = ['grant_teacher_access', 'revoke_teacher_access']

    @admin.display(description='角色')
    def role_badge(self, obj):
        fg, bg = ('#3730a3', '#eef2ff') if obj.role == 'teacher' else ('#166534', '#dcfce7')
        return _badge(obj.get_role_display(), fg, bg)

    @admin.display(description='快速登入')
    def oauth_badge(self, obj):
        if obj.google_id:
            return _badge('Google', '#1d4ed8', '#dbeafe')
        if obj.line_id:
            return _badge('LINE', '#166534', '#dcfce7')
        return '—'

    @admin.action(description='✅ 賦予教師權限')
    def grant_teacher_access(self, request, queryset):
        n = queryset.update(is_teacher=True)
        self.message_user(request, f'已賦予 {n} 位使用者教師權限。')

    @admin.action(description='⛔ 收回教師權限')
    def revoke_teacher_access(self, request, queryset):
        n = queryset.update(is_teacher=False)
        self.message_user(request, f'已收回 {n} 位使用者的教師權限。')


class ProfileInline(admin.StackedInline):
    """讓 Admin 直接在使用者編輯頁勾選是否給予教師身分，不用切去另一頁。"""
    model = Profile
    can_delete = False
    extra = 0
    max_num = 1
    fields = ('is_teacher',)
    verbose_name = '教師專區權限'
    verbose_name_plural = '教師專區權限'


class CustomUserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ===== 課程 =====
class RevenueShareSliderWidget(forms.NumberInput):
    """分潤比例拉桿：拖動時即時顯示百分比，平台分潤 = 100 - 教師分潤。"""
    input_type = 'range'

    def render(self, name, value, attrs=None, renderer=None):
        attrs = {**(attrs or {}), 'min': 0, 'max': 100, 'step': 5,
                 'oninput': 'this.nextElementSibling.value = this.value + "% 教師 / " + (100 - this.value) + "% 平台"',
                 'style': 'width:260px;vertical-align:middle;'}
        input_html = super().render(name, value, attrs, renderer)
        display_value = f'{value}% 教師 / {100 - int(value)}% 平台' if value not in (None, '') else '70% 教師 / 30% 平台'
        return format_html(
            '{} <output style="font-weight:700;margin-left:10px;">{}</output>',
            input_html, display_value
        )


class CourseAdminForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = '__all__'
        widgets = {
            'teacher_revenue_share': RevenueShareSliderWidget,
        }


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'course_count', 'created_at')
    search_fields = ('name',)

    @admin.display(description='課程數')
    def course_count(self, obj):
        return obj.course_set.count()


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ('title', 'teacher', 'category', 'level', 'price', 'revenue_share_display', 'promo_badge', 'published_badge', 'created_at')
    list_editable = ('price',)
    list_display_links = ('title',)
    search_fields = ('title', 'teacher__username', 'category__name')
    list_filter = ('is_published', 'level', 'category', 'teacher', 'promo_video_type')
    # 'teacher' 改用限制過名單的一般下拉選單（見 formfield_for_foreignkey），
    # 不用 autocomplete：AJAX 搜尋走 User 自己的 admin，不會套用這裡的名單限制。
    autocomplete_fields = ('category',)
    list_per_page = 25
    inlines = [CourseChapterInline]
    actions = ['make_published', 'make_unpublished']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'teacher':
            kwargs['queryset'] = User.objects.filter(
                profile__is_teacher=True
            ).order_by('username')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='上架狀態')
    def published_badge(self, obj):
        return status_badge('paid' if obj.is_published else 'pending',
                            '已上架' if obj.is_published else '未上架')

    @admin.display(description='分潤（師/平台）')
    def revenue_share_display(self, obj):
        return f'{obj.teacher_revenue_share}% / {obj.platform_revenue_share()}%'

    @admin.display(description='宣傳模式')
    def promo_badge(self, obj):
        colors = {
            'NONE': ('#475569', '#e2e8f0'),
            'PHYSICAL_SHOOT': ('#3730a3', '#eef2ff'),
            'AI_GENERATED': ('#9d174d', '#fce7f3'),
        }
        fg, bg = colors.get(obj.promo_video_type, ('#475569', '#e2e8f0'))
        return _badge(obj.get_promo_video_type_display(), fg, bg)

    @admin.action(description='✅ 上架選取的課程')
    def make_published(self, request, queryset):
        n = queryset.update(is_published=True)
        self.message_user(request, f'已上架 {n} 門課程。')

    @admin.action(description='⛔ 下架選取的課程')
    def make_unpublished(self, request, queryset):
        n = queryset.update(is_published=False)
        self.message_user(request, f'已下架 {n} 門課程。')


@admin.register(CourseChapter)
class CourseChapterAdmin(admin.ModelAdmin):
    list_display = ('course', 'sort_order', 'title', 'lesson_count')
    search_fields = ('course__title', 'title')
    list_filter = ('course',)
    autocomplete_fields = ('course',)
    ordering = ('course', 'sort_order')
    inlines = [CourseLessonInline]

    @admin.display(description='單元數')
    def lesson_count(self, obj):
        return obj.lessons.count()


@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'sort_order', 'title', 'duration_minutes', 'has_video', 'free_badge')
    search_fields = ('chapter__course__title', 'chapter__title', 'title')
    list_filter = ('chapter__course', 'is_free_preview')
    ordering = ('chapter', 'sort_order')

    @admin.display(description='影片')
    def has_video(self, obj):
        if obj.video_file:
            return _badge('已上傳', '#166534', '#dcfce7')
        if obj.video_url:
            return _badge('連結', '#3730a3', '#eef2ff')
        return _badge('無', '#991b1b', '#fee2e2')

    @admin.display(description='試看')
    def free_badge(self, obj):
        return '免費' if obj.is_free_preview else '—'


@admin.register(CourseAudit)
class CourseAuditAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher_name', 'audit_badge', 'created_at', 'reviewed_at')
    search_fields = ('course__title', 'reviewer__username', 'comment')
    list_filter = ('status', 'created_at')
    autocomplete_fields = ('course', 'reviewer')

    @admin.display(description='講師')
    def teacher_name(self, obj):
        return obj.course.teacher.username

    @admin.display(description='審核狀態')
    def audit_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())


# ===== 交易 =====
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'original_price', 'discount_amount', 'final_price', 'order_badge', 'created_at')
    list_display_links = ('id', 'user')
    search_fields = ('user__username', 'course__title')
    list_filter = ('status', 'created_at')
    autocomplete_fields = ('user', 'course', 'coupon')
    list_per_page = 25
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = ('created_at',)

    @admin.display(description='訂單狀態')
    def order_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'course', 'price')
    search_fields = ('order__user__username', 'course__title')
    autocomplete_fields = ('order', 'course')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'amount', 'payment_badge', 'transaction_no', 'paid_at')
    search_fields = ('order__user__username', 'transaction_no')
    list_filter = ('method', 'status', 'created_at')

    @admin.display(description='付款狀態')
    def payment_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'amount', 'refund_badge', 'created_at', 'processed_at')
    search_fields = ('user__username', 'order__id')
    list_filter = ('status', 'created_at')
    autocomplete_fields = ('order', 'user')
    actions = ['approve_refund', 'reject_refund']

    @admin.display(description='退款狀態')
    def refund_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())

    @admin.action(description='✅ 核准退款')
    def approve_refund(self, request, queryset):
        n = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f'已核准 {n} 筆退款。')

    @admin.action(description='⛔ 拒絕退款')
    def reject_refund(self, request, queryset):
        n = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'已拒絕 {n} 筆退款。')


@admin.register(TeacherBankAccount)
class TeacherBankAccountAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'bank_name', 'branch_name', 'account_name', 'account_number', 'updated_at')
    search_fields = ('teacher__username', 'bank_name', 'account_name', 'account_number')
    autocomplete_fields = ('teacher',)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'amount', 'withdrawal_badge', 'created_at', 'processed_at')
    search_fields = ('teacher__username',)
    list_filter = ('status', 'created_at')
    autocomplete_fields = ('teacher',)
    readonly_fields = ('bank_info_snapshot', 'created_at')
    actions = ['approve_withdrawal', 'reject_withdrawal']

    @admin.display(description='審核狀態')
    def withdrawal_badge(self, obj):
        colors = {'PENDING': 'pending', 'APPROVED': 'approved', 'REJECTED': 'rejected'}
        return status_badge(colors.get(obj.status, obj.status), obj.get_status_display())

    @admin.action(description='✅ 核准提領')
    def approve_withdrawal(self, request, queryset):
        n = queryset.filter(status='PENDING').update(status='APPROVED', processed_at=timezone.now())
        self.message_user(request, f'已核准 {n} 筆提領申請。')

    @admin.action(description='⛔ 拒絕提領')
    def reject_withdrawal(self, request, queryset):
        n = queryset.filter(status='PENDING').update(status='REJECTED', processed_at=timezone.now())
        self.message_user(request, f'已拒絕 {n} 筆提領申請。')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'purchased_at')
    search_fields = ('student__username', 'course__title')
    list_filter = ('purchased_at', 'course')
    autocomplete_fields = ('student', 'course')


# ===== 行銷 =====
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'discount_type', 'discount_value', 'min_spend', 'end_date', 'is_active', 'current_status')
    list_editable = ('is_active',)
    search_fields = ('code', 'name')
    list_filter = ('discount_type', 'is_active')

    @admin.display(description='目前狀態')
    def current_status(self, obj):
        return status_badge(obj.status_label(), obj.status_label())


@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'status', 'current_status', 'received_at', 'used_at')
    search_fields = ('user__username', 'coupon__code')
    list_filter = ('status', 'received_at')
    autocomplete_fields = ('user', 'coupon')

    @admin.display(description='實際狀態')
    def current_status(self, obj):
        return status_badge(obj.effective_status(), obj.effective_status())


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'order', 'discount_amount', 'used_at')
    search_fields = ('user__username', 'coupon__code', 'order__course__title')
    list_filter = ('used_at',)
    autocomplete_fields = ('user', 'coupon', 'order')


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)
    list_filter = ('discount_type', 'is_active')
    filter_horizontal = ('courses',)


# ===== 購物車 =====
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_count', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

    @admin.display(description='商品數')
    def item_count(self, obj):
        return obj.items.count()


# ===== 學習 / 互動 =====
@admin.register(LearningRecord)
class LearningRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'lesson', 'minutes', 'watched_at')
    search_fields = ('user__username', 'course__title', 'lesson__title')
    list_filter = ('course', 'watched_at')
    autocomplete_fields = ('user', 'course', 'lesson')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'percent_display', 'last_position', 'duration', 'is_completed', 'updated_at')
    search_fields = ('user__username', 'lesson__title', 'course__title')
    list_filter = ('is_completed', 'updated_at')
    autocomplete_fields = ('user', 'course', 'lesson')

    @admin.display(description='觀看進度')
    def percent_display(self, obj):
        return f'{obj.percent()}%'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'created_at')
    search_fields = ('user__username', 'course__title')
    list_filter = ('created_at',)
    autocomplete_fields = ('user', 'course')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'star_display', 'short_comment', 'created_at')
    search_fields = ('user__username', 'course__title', 'comment')
    list_filter = ('rating', 'created_at')
    autocomplete_fields = ('user', 'course')

    @admin.display(description='評分')
    def star_display(self, obj):
        return format_html('<span style="color:#f59e0b;font-weight:700;">{}</span>', '★' * obj.rating)

    @admin.display(description='評論')
    def short_comment(self, obj):
        if not obj.comment:
            return '—'
        return (obj.comment[:20] + '…') if len(obj.comment) > 20 else obj.comment


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'read_badge', 'created_at')
    search_fields = ('user__username', 'title', 'content')
    list_filter = ('is_read', 'created_at')
    autocomplete_fields = ('user',)
    actions = ['mark_read']

    @admin.display(description='狀態')
    def read_badge(self, obj):
        return _badge('已讀', '#475569', '#e2e8f0') if obj.is_read else _badge('未讀', '#92400e', '#fef3c7')

    @admin.action(description='標記為已讀')
    def mark_read(self, request, queryset):
        n = queryset.update(is_read=True)
        self.message_user(request, f'已標記 {n} 則通知為已讀。')


@admin.register(CourseQuestion)
class CourseQuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'user', 'answer_count', 'created_at')
    search_fields = ('title', 'content', 'course__title', 'user__username')
    list_filter = ('course', 'created_at')
    autocomplete_fields = ('user', 'course', 'lesson')
    inlines = [CourseAnswerInline]

    @admin.display(description='回答數')
    def answer_count(self, obj):
        return obj.answers.count()


@admin.register(CourseAnswer)
class CourseAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'created_at')
    search_fields = ('question__title', 'user__username', 'content')
    list_filter = ('created_at',)
    autocomplete_fields = ('question', 'user')


# ===== 後台側邊選單自訂分組（課程 / 交易 / 行銷 / 會員） =====
from django.urls import reverse as _reverse

_CUSTOM_GROUPS = [
    ('📚 課程管理', ['Course', 'CourseCategory', 'CourseChapter', 'CourseLesson', 'CourseAudit']),
    ('🧾 交易管理', ['Order', 'OrderItem', 'Payment', 'Refund', 'Enrollment']),
    ('🎯 行銷管理', ['Coupon', 'UserCoupon', 'CouponUsage', 'Promotion', 'Cart']),
    ('👥 會員與互動', ['Profile', 'LearningRecord', 'LessonProgress', 'Favorite', 'Review', 'Notification', 'CourseQuestion', 'CourseAnswer']),
    ('💸 教師分潤與提領', ['TeacherBankAccount', 'WithdrawalRequest']),
]

_ORDER_INDEX = {
    name: (gi, mi)
    for gi, (_, names) in enumerate(_CUSTOM_GROUPS)
    for mi, name in enumerate(names)
}

_original_get_app_list = admin.AdminSite.get_app_list


def _grouped_get_app_list(self, request, app_label=None):
    # 單一 app 頁面維持預設行為
    if app_label:
        return _original_get_app_list(self, request, app_label)

    app_dict = self._build_app_dict(request)
    models_by_name = {}
    for app in app_dict.values():
        for m in app['models']:
            models_by_name[m['object_name']] = m

    main_url = _reverse('admin:app_list', kwargs={'app_label': 'main'})
    result = []
    used = set()

    for gi, (group_name, names) in enumerate(_CUSTOM_GROUPS):
        models = []
        for n in names:
            m = models_by_name.get(n)
            if m:
                models.append(m)
                used.add(n)
        # 組內依指定順序排序
        models.sort(key=lambda md: _ORDER_INDEX.get(md['object_name'], (99, 99))[1])
        if models:
            result.append({
                'name': group_name,
                'app_label': f'group_{gi}',
                'app_url': main_url,
                'has_module_perms': True,
                'models': models,
            })

    # 其餘未分組（如帳號 User/Group）
    leftover = []
    for app in app_dict.values():
        for m in app['models']:
            if m['object_name'] not in used:
                leftover.append(m)
    if leftover:
        try:
            auth_url = _reverse('admin:app_list', kwargs={'app_label': 'auth'})
        except Exception:
            auth_url = main_url
        result.append({
            'name': '⚙️ 系統與帳號',
            'app_label': 'group_sys',
            'app_url': auth_url,
            'has_module_perms': True,
            'models': leftover,
        })

    return result


admin.AdminSite.get_app_list = _grouped_get_app_list
