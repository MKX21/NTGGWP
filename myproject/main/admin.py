from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html

from . import transitions
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
    CourseBundle,
    CourseAnnouncement,
    CourseComment,
    CourseSplitSetting,
    RevenueRecord,
    WithdrawalRequest,
    TeacherFollow,
    TeacherColumn,
    TeacherArticle,
    TeacherMaterial,
    UserBadge,
    ColumnSubscription,
    TeacherBankAccount,
    MarketingRequest,
    MarketingPlan,
    VMAccessRequest,
    CourseCertificate,
)

admin.site.site_header = "購課平台・營運管理後台"
admin.site.site_title = "課程平台後台"
admin.site.index_title = "營運管理總覽"
admin.site.index_template = "admin/custom_index.html"

def _badge(text, fg, bg):
    return format_html(
        '<span style="padding:3px 10px;border-radius:999px;font-size:12px;'
        'font-weight:700;color:{};background:{};white-space:nowrap;">{}</span>',
        fg, bg, text,
    )

STATUS_COLORS = {
    'pending': ('#92400e', '#fef3c7'),
    'paid': ('#166534', '#dcfce7'),
    'cancelled': ('#475569', '#e2e8f0'),
    'refunded': ('#991b1b', '#fee2e2'),
    'failed': ('#991b1b', '#fee2e2'),
    'approved': ('#166534', '#dcfce7'),
    'rejected': ('#991b1b', '#fee2e2'),
    'completed': ('#166534', '#dcfce7'),
    'unused': ('#166534', '#dcfce7'),
    'used': ('#475569', '#e2e8f0'),
    'expired': ('#991b1b', '#fee2e2'),
    'confirmed': ('#166534', '#dcfce7'),
    'reversed': ('#991b1b', '#fee2e2'),
    '已過期': ('#991b1b', '#fee2e2'),
    '使用中': ('#166534', '#dcfce7'),
    '未開始': ('#92400e', '#fef3c7'),
    '已停用': ('#475569', '#e2e8f0'),
    '已用完': ('#475569', '#e2e8f0'),
}

def status_badge(value, label=None):
    fg, bg = STATUS_COLORS.get(value, ('#334155', '#e2e8f0'))
    return _badge(label or value, fg, bg)

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

class CourseSplitSettingInline(admin.StackedInline):
    model = CourseSplitSetting
    extra = 0
    max_num = 1
    can_delete = False
    fields = (
        ('teacher_split_percent', 'company_split_percent'),
        ('teacher_marketing_share_percent', 'company_marketing_share_percent'),
    )

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

class RevenueShareSliderWidget(forms.NumberInput):
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
    autocomplete_fields = ('category',)
    list_per_page = 25
    inlines = [CourseChapterInline, CourseSplitSettingInline]
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

    @admin.action(description='✅ 審核通過並上架選取的課程')
    def make_published(self, request, queryset):
        courses = list(queryset)
        for course in courses:
            transitions.approve_course(course, request.user, comment='後台批次核准')
        self.message_user(request, f'已上架 {len(courses)} 門課程。')

    @admin.action(description='⛔ 退回並下架選取的課程')
    def make_unpublished(self, request, queryset):
        courses = list(queryset)
        for course in courses:
            transitions.reject_course(course, request.user, comment='後台批次退回')
        self.message_user(request, f'已下架 {len(courses)} 門課程。')

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

class CourseBundleAdminForm(forms.ModelForm):
    class Meta:
        model = CourseBundle
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        bundle_price = cleaned.get('bundle_price')
        courses = cleaned.get('courses')
        if bundle_price and courses:
            total = sum(c.get_effective_price() for c in courses)
            if bundle_price >= total:
                self.add_error('bundle_price', f'合購價必須低於課程原價總和（NT$ {total}），否則不是優惠。')
        return cleaned

@admin.register(CourseBundle)
class CourseBundleAdmin(admin.ModelAdmin):
    form = CourseBundleAdminForm
    list_display = ('name', 'course_count', 'total_individual_price_display', 'bundle_price', 'savings_display', 'active_badge', 'created_at')
    filter_horizontal = ('courses',)
    search_fields = ('name',)
    list_filter = ('is_active',)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'courses':
            kwargs['queryset'] = Course.objects.filter(is_published=True).order_by('title')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(description='課程數')
    def course_count(self, obj):
        return obj.courses.count()

    @admin.display(description='原價總和')
    def total_individual_price_display(self, obj):
        return f'NT$ {obj.total_individual_price()}'

    @admin.display(description='折抵金額')
    def savings_display(self, obj):
        return f'NT$ {obj.savings()}'

    @admin.display(description='狀態')
    def active_badge(self, obj):
        return status_badge('paid' if obj.is_active else 'cancelled', '啟用中' if obj.is_active else '已停用')

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
    list_display = ('order', 'course', 'price', 'discount_amount', 'paid_amount')
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

    def save_model(self, request, obj, form, change):
        if change and 'status' in getattr(form, 'changed_data', []):
            previous = Refund.objects.filter(pk=obj.pk).first()
            if previous and previous.status == 'pending':
                if obj.status in ('approved', 'completed'):
                    obj.status = 'pending'
                    transitions.approve_refund(obj)
                    return
                if obj.status == 'rejected':
                    obj.status = 'pending'
                    transitions.reject_refund(obj)
                    return
        super().save_model(request, obj, form, change)

    @admin.display(description='退款狀態')
    def refund_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())

    @admin.action(description='✅ 核准退款')
    def approve_refund(self, request, queryset):
        pending = list(queryset.filter(status='pending').select_related('order', 'user'))
        for refund in pending:
            transitions.approve_refund(refund)
        self.message_user(
            request,
            f'已核准 {len(pending)} 筆退款，對應的課程存取權已收回、付款已回沖。'
        )

    @admin.action(description='⛔ 拒絕退款')
    def reject_refund(self, request, queryset):
        pending = list(queryset.filter(status='pending').select_related('order', 'user'))
        for refund in pending:
            transitions.reject_refund(refund)
        self.message_user(request, f'已拒絕 {len(pending)} 筆退款。')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'purchased_at')
    search_fields = ('student__username', 'course__title')
    list_filter = ('purchased_at', 'course')
    autocomplete_fields = ('student', 'course')


@admin.register(CourseCertificate)
class CourseCertificateAdmin(admin.ModelAdmin):
    list_display = ('display_number', 'student', 'course', 'issued_at')
    search_fields = ('certificate_number', 'student__username', 'course__title')
    list_filter = ('issued_at', 'course')
    autocomplete_fields = ('student', 'course')
    readonly_fields = ('certificate_number', 'student', 'course', 'issued_at')

    @admin.display(description='證書編號')
    def display_number(self, obj):
        return obj.display_number

@admin.register(CourseSplitSetting)
class CourseSplitSettingAdmin(admin.ModelAdmin):
    list_display = (
        'course', 'teacher_split_percent', 'company_split_percent',
        'teacher_marketing_share_percent', 'company_marketing_share_percent', 'updated_at',
    )
    search_fields = ('course__title', 'course__teacher__username')
    autocomplete_fields = ('course',)

@admin.register(RevenueRecord)
class RevenueRecordAdmin(admin.ModelAdmin):
    list_display = (
        'course', 'teacher', 'order', 'gross_amount', 'marketing_cost',
        'teacher_amount', 'company_amount', 'revenue_badge', 'created_at',
    )
    search_fields = ('course__title', 'teacher__username', 'order__id')
    list_filter = ('status', 'created_at')
    autocomplete_fields = ('order', 'order_item', 'course', 'teacher')
    readonly_fields = (
        'order_item', 'order', 'course', 'teacher', 'gross_amount',
        'teacher_split_percent', 'company_split_percent',
        'teacher_marketing_share_percent', 'company_marketing_share_percent',
        'teacher_amount', 'company_amount', 'created_at', 'reversed_at',
    )

    @admin.display(description='狀態')
    def revenue_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())

    def has_add_permission(self, request):
        return False

@admin.register(TeacherBankAccount)
class TeacherBankAccountAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'bank_name', 'bank_code', 'account_name', 'account_number', 'updated_at')
    search_fields = ('teacher__username', 'bank_name', 'account_name', 'account_number')
    autocomplete_fields = ('teacher',)

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'amount', 'withdrawal_badge', 'requested_at', 'processed_at')
    search_fields = ('teacher__username',)
    list_filter = ('status', 'requested_at')
    autocomplete_fields = ('teacher',)
    actions = ['mark_completed', 'mark_rejected']

    @admin.display(description='狀態')
    def withdrawal_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())

    @admin.action(description='✅ 標記為已完成')
    def mark_completed(self, request, queryset):
        pending = list(queryset.filter(status='pending').select_related('teacher'))
        for withdrawal in pending:
            transitions.complete_withdrawal(withdrawal)
        self.message_user(request, f'已標記 {len(pending)} 筆提領為已完成。')

    @admin.action(description='⛔ 拒絕提領')
    def mark_rejected(self, request, queryset):
        pending = list(queryset.filter(status='pending').select_related('teacher'))
        for withdrawal in pending:
            transitions.reject_withdrawal(withdrawal)
        self.message_user(request, f'已拒絕 {len(pending)} 筆提領申請。')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'discount_type', 'discount_value', 'min_spend', 'end_date', 'is_active', 'current_status')
    list_editable = ('is_active',)
    search_fields = ('code', 'name')
    list_filter = ('discount_type', 'is_active')
    actions = ['broadcast_to_members']

    @admin.display(description='目前狀態')
    def current_status(self, obj):
        return status_badge(obj.status_label(), obj.status_label())

    @admin.action(description='📣 推播選取的優惠券給所有會員')
    def broadcast_to_members(self, request, queryset):
        from .notifications import notify_users
        member_ids = list(User.objects.filter(is_active=True).values_list('id', flat=True))
        total = 0
        for coupon in queryset:
            total += notify_users(
                member_ids,
                f'新優惠券上線：{coupon.name}',
                f'輸入優惠碼「{coupon.code}」即可享有折扣，快到購物車使用！'
            )
        self.message_user(
            request,
            f'已將 {queryset.count()} 張優惠券推播給 {len(member_ids)} 位會員（共 {total} 則通知）。'
        )

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

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_count', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

    @admin.display(description='商品數')
    def item_count(self, obj):
        return obj.items.count()

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
    list_display = ('question', 'user', 'is_ai_generated', 'created_at')
    search_fields = ('question__title', 'user__username', 'content')
    list_filter = ('is_ai_generated', 'created_at')
    autocomplete_fields = ('question', 'user')

@admin.register(CourseAnnouncement)
class CourseAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('course', 'author', 'title', 'created_at')
    search_fields = ('title', 'content', 'course__title')
    list_filter = ('created_at',)
    autocomplete_fields = ('course', 'author')

@admin.register(CourseComment)
class CourseCommentAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'short_content', 'created_at')
    search_fields = ('content', 'course__title', 'user__username')
    list_filter = ('created_at',)
    autocomplete_fields = ('course', 'user')

    @admin.display(description='留言')
    def short_content(self, obj):
        return (obj.content[:20] + '…') if len(obj.content) > 20 else obj.content

@admin.register(TeacherFollow)
class TeacherFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'teacher', 'created_at')
    search_fields = ('follower__username', 'teacher__username')
    list_filter = ('created_at',)
    autocomplete_fields = ('follower', 'teacher')

@admin.register(TeacherColumn)
class TeacherColumnAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'is_published', 'created_at')
    search_fields = ('title', 'teacher__username')
    list_filter = ('is_published', 'created_at')
    autocomplete_fields = ('teacher',)

@admin.register(TeacherArticle)
class TeacherArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'column', 'is_published', 'created_at')
    search_fields = ('title', 'content', 'teacher__username')
    list_filter = ('is_published', 'created_at')
    autocomplete_fields = ('teacher', 'column')

@admin.register(TeacherMaterial)
class TeacherMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'is_published', 'created_at')
    search_fields = ('title', 'description', 'teacher__username')
    list_filter = ('is_published', 'created_at')
    autocomplete_fields = ('teacher',)

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'earned_at')
    search_fields = ('user__username', 'code')
    list_filter = ('code', 'earned_at')
    autocomplete_fields = ('user',)

@admin.register(ColumnSubscription)
class ColumnSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'column', 'started_at', 'expires_at')
    search_fields = ('user__username', 'column__title')
    list_filter = ('started_at', 'expires_at')
    autocomplete_fields = ('user', 'column')

from django.urls import reverse as _reverse

_CUSTOM_GROUPS = [
    ('📚 課程管理', ['Course', 'CourseCategory', 'CourseChapter', 'CourseLesson', 'CourseAudit', 'CourseBundle', 'CourseAnnouncement']),
    ('🧾 交易管理', ['Order', 'OrderItem', 'Payment', 'Refund', 'Enrollment', 'CourseCertificate']),
    ('💰 分潤與提領', ['CourseSplitSetting', 'RevenueRecord', 'WithdrawalRequest', 'TeacherBankAccount']),
    ('🎯 行銷管理', ['MarketingRequest', 'MarketingPlan', 'Coupon', 'UserCoupon', 'CouponUsage', 'Promotion', 'Cart']),
    ('📝 講師內容', ['TeacherColumn', 'TeacherArticle', 'TeacherMaterial', 'ColumnSubscription']),
    ('👥 會員與互動', ['Profile', 'TeacherFollow', 'UserBadge', 'LearningRecord', 'LessonProgress', 'Favorite', 'Review', 'Notification', 'CourseQuestion', 'CourseAnswer', 'CourseComment']),
    ('🖥️ 虛擬機服務', ['VMAccessRequest']),
]

_ORDER_INDEX = {
    name: (gi, mi)
    for gi, (_, names) in enumerate(_CUSTOM_GROUPS)
    for mi, name in enumerate(names)
}

_original_get_app_list = admin.AdminSite.get_app_list

def _grouped_get_app_list(self, request, app_label=None):
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
        models.sort(key=lambda md: _ORDER_INDEX.get(md['object_name'], (99, 99))[1])
        if models:
            result.append({
                'name': group_name,
                'app_label': f'group_{gi}',
                'app_url': main_url,
                'has_module_perms': True,
                'models': models,
            })

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

class MarketingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = MarketingRequest
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('status') == 'completed' and self.instance.pk:
            has_approved_plan = MarketingPlan.objects.filter(
                marketing_request=self.instance, status='approved'
            ).exists()
            if not has_approved_plan:
                raise forms.ValidationError(
                    '這筆申請還沒有已核准的企劃，無法標記為已完成。'
                    '請先用「AI 生成行銷企劃」產生，並在 AI 行銷企劃列表核准。'
                )
        return cleaned

@admin.register(MarketingRequest)
class MarketingRequestAdmin(admin.ModelAdmin):
    form = MarketingRequestAdminForm

    list_display = (
        'course',
        'teacher',
        'goal_display',
        'status_badge',
        'desired_start_date',
        'created_at',
    )

    list_filter = (
        'status',
        'goal',
        'desired_start_date',
        'created_at',
    )

    search_fields = (
        'course__title',
        'teacher__username',
        'teacher__email',
        'notes',
        'admin_note',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    list_select_related = (
        'course',
        'teacher',
    )

    list_per_page = 25

    fieldsets = (
        (
            '申請資訊',
            {
                'fields': (
                    'course',
                    'teacher',
                    'goal',
                    'desired_start_date',
                    'notes',
                )
            }
        ),
        (
            '後台處理',
            {
                'fields': (
                    'status',
                    'admin_note',
                )
            }
        ),
        (
            '時間',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    @admin.display(description='行銷目的')
    def goal_display(self, obj):
        return obj.get_goal_display()

    @admin.display(description='申請狀態')
    def status_badge(self, obj):
        return status_badge(
            obj.status,
            obj.get_status_display()
        )

    @admin.action(description='標記為處理中')
    def mark_processing(self, request, queryset):
        count = queryset.filter(
            status='pending'
        ).update(
            status='processing',
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'已將 {count} 筆行銷申請標記為處理中。'
        )

    @admin.action(description='標記為已完成')
    def mark_completed(self, request, queryset):
        eligible = queryset.filter(
            status='processing',
            plan__status='approved',
        )
        skipped = queryset.filter(status='processing').exclude(id__in=eligible).count()
        count = eligible.update(
            status='completed',
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'已將 {count} 筆行銷申請標記為已完成。'
        )
        if skipped:
            self.message_user(
                request,
                f'{skipped} 筆申請尚未有已核准的企劃，請先用「AI 生成行銷企劃」產生，'
                f'並在 AI 行銷企劃列表核准後，才能標記為已完成。',
                level='warning',
            )

    @admin.action(description='退回行銷申請')
    def mark_rejected(self, request, queryset):
        count = queryset.exclude(
            status='completed'
        ).update(
            status='rejected',
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'已退回 {count} 筆行銷申請。'
        )

    @admin.action(description='AI 生成行銷企劃')
    def generate_ai_plan(self, request, queryset):
        from .ai_marketing import create_or_update_plan
        success_count = 0
        fail_messages = []
        for mreq in queryset.filter(status__in=['pending', 'processing']):
            ok, msg, plan = create_or_update_plan(mreq)
            if ok:
                success_count += 1
                Notification.objects.create(
                    user=mreq.teacher,
                    title='行銷企劃已生成',
                    content=f'您的課程「{mreq.course.title}」的 AI 行銷企劃已生成，等待管理員審核。'
                )
            else:
                fail_messages.append(f'{mreq.course.title}: {msg}')

        if success_count:
            self.message_user(
                request,
                f'已成功為 {success_count} 筆申請生成 AI 行銷企劃。'
            )
        for fm in fail_messages:
            self.message_user(request, f'生成失敗 - {fm}', level='error')

    actions = [
        'mark_processing',
        'mark_completed',
        'mark_rejected',
        'generate_ai_plan',
    ]

@admin.register(MarketingPlan)
class MarketingPlanAdmin(admin.ModelAdmin):
    list_display = (
        'course_title',
        'teacher',
        'status_badge',
        'generated_at',
        'reviewed_at',
    )

    list_filter = (
        'status',
        'generated_at',
        'reviewed_at',
    )

    search_fields = (
        'marketing_request__course__title',
        'marketing_request__teacher__username',
        'target_audience',
        'marketing_strategy',
        'ad_headline',
        'ad_copy',
    )

    readonly_fields = (
        'generated_at',
        'created_at',
        'updated_at',
    )

    list_select_related = (
        'marketing_request',
        'marketing_request__course',
        'marketing_request__teacher',
    )

    list_per_page = 25

    fieldsets = (
        (
            '基本資訊',
            {
                'fields': (
                    'marketing_request',
                    'status',
                )
            }
        ),
        (
            'AI 行銷分析',
            {
                'fields': (
                    'target_audience',
                    'course_selling_points',
                    'marketing_strategy',
                )
            }
        ),
        (
            'AI 廣告內容',
            {
                'fields': (
                    'ad_headline',
                    'ad_copy',
                    'social_media_copy',
                    'video_script',
                    'call_to_action',
                )
            }
        ),
        (
            '管理員審核',
            {
                'fields': (
                    'admin_note',
                    'reviewed_at',
                )
            }
        ),
        (
            '系統資訊',
            {
                'fields': (
                    'generated_at',
                    'created_at',
                    'updated_at',
                )
            }
        ),
    )

    actions = [
        'approve_plans',
        'reject_plans',
        'regenerate_plans',
    ]

    @admin.display(description='課程')
    def course_title(self, obj):
        return obj.marketing_request.course.title

    @admin.display(description='教師')
    def teacher(self, obj):
        return obj.marketing_request.teacher.username

    @admin.display(description='企劃狀態')
    def status_badge(self, obj):
        return status_badge(
            obj.status,
            obj.get_status_display()
        )

    @admin.action(description='核准選取的 AI 行銷企劃')
    def approve_plans(self, request, queryset):
        count = 0
        for plan in queryset.filter(status__in=['reviewing', 'draft']):
            plan.status = 'approved'
            plan.reviewed_at = timezone.now()
            plan.save(update_fields=['status', 'reviewed_at', 'updated_at'])
            plan.marketing_request.status = 'completed'
            plan.marketing_request.save(update_fields=['status', 'updated_at'])
            Notification.objects.create(
                user=plan.marketing_request.teacher,
                title='行銷企劃已核准',
                content=f'您的課程「{plan.marketing_request.course.title}」的 AI 行銷企劃已核准，請至行銷申請頁面查看完整內容。'
            )
            count += 1
        self.message_user(request, f'已核准 {count} 份 AI 行銷企劃。')

    @admin.action(description='退回選取的 AI 行銷企劃')
    def reject_plans(self, request, queryset):
        count = 0
        for plan in queryset.exclude(status='approved'):
            plan.status = 'rejected'
            plan.reviewed_at = timezone.now()
            plan.save(update_fields=['status', 'reviewed_at', 'updated_at'])
            plan.marketing_request.status = 'rejected'
            plan.marketing_request.save(update_fields=['status', 'updated_at'])
            note = plan.admin_note or '（未填寫原因）'
            Notification.objects.create(
                user=plan.marketing_request.teacher,
                title='行銷企劃已退回',
                content=f'您的課程「{plan.marketing_request.course.title}」的行銷企劃已退回。備註：{note}'
            )
            count += 1
        self.message_user(request, f'已退回 {count} 份 AI 行銷企劃。')

    @admin.action(description='重新生成 AI 行銷企劃')
    def regenerate_plans(self, request, queryset):
        from .ai_marketing import create_or_update_plan
        success_count = 0
        for plan in queryset:
            ok, msg, _ = create_or_update_plan(plan.marketing_request)
            if ok:
                success_count += 1
            else:
                self.message_user(request, f'重新生成失敗: {msg}', level='error')
        if success_count:
            self.message_user(request, f'已重新生成 {success_count} 份 AI 行銷企劃。')

class VMAccessRequestAdminForm(forms.ModelForm):
    class Meta:
        model = VMAccessRequest
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('status') == 'approved':
            missing = [
                label for field, label in (
                    ('vm_url', '虛擬機網址'),
                    ('vm_username', '虛擬機帳號'),
                    ('vm_password', '虛擬機密碼'),
                )
                if not (cleaned.get(field) or '').strip()
            ]
            if missing:
                raise forms.ValidationError(
                    f'標記為已核發前，請先填寫：{"、".join(missing)}。'
                )
        return cleaned

@admin.register(VMAccessRequest)
class VMAccessRequestAdmin(admin.ModelAdmin):
    form = VMAccessRequestAdminForm

    list_display = ('student', 'course', 'status_badge', 'created_at', 'approved_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__username', 'student__email', 'course__title')
    list_select_related = ('student', 'course')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    actions = ['reject_requests']

    fieldsets = (
        ('申請資訊（先確認申請人確實購買過此課程）', {
            'fields': ('student', 'course', 'reason'),
        }),
        ('核發虛擬機連線資訊', {
            'fields': ('vm_url', 'vm_username', 'vm_password'),
            'description': '三個欄位都填好、狀態改成「已核發」並儲存後，系統會自動通知學生。',
        }),
        ('後台處理', {
            'fields': ('status', 'admin_note'),
        }),
        ('時間', {
            'fields': ('created_at', 'updated_at', 'approved_at'),
        }),
    )

    @admin.display(description='申請狀態')
    def status_badge(self, obj):
        return status_badge(obj.status, obj.get_status_display())

    def save_model(self, request, obj, form, change):
        was_approved = False
        if change and obj.pk:
            was_approved = VMAccessRequest.objects.filter(
                pk=obj.pk, status='approved'
            ).exists()

        if obj.status == 'approved' and not obj.approved_at:
            obj.approved_at = timezone.now()

        super().save_model(request, obj, form, change)

        if obj.status == 'approved' and not was_approved:
            Notification.objects.create(
                user=obj.student,
                title='虛擬機已核發',
                content=(
                    f'你申請的「{obj.course.title}」虛擬機已核發，'
                    f'請至「我的虛擬機」頁面查看連線資訊。'
                )
            )

    @admin.action(description='退回選取的申請')
    def reject_requests(self, request, queryset):
        count = queryset.exclude(status='approved').update(
            status='rejected', updated_at=timezone.now()
        )
        self.message_user(request, f'已退回 {count} 筆虛擬機申請。')
