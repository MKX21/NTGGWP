import csv
import json
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import (
    Avg,
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
)
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme, urlencode

from django.utils import timezone

from .models import (
    Course,
    CourseLesson,
    CourseSplitSetting,
    Profile,
    Enrollment,
    LearningRecord,
    LessonProgress,
    Coupon,
    Order,
    OrderItem,
    CouponUsage,
    Payment,
    Notification,
    RevenueRecord,
    Review,
    Cart,
    CartItem,
    Favorite,
    Refund,
    UserCoupon,
    CourseChapter,
    CourseQuestion,
    CourseAnswer,
    CourseAudit,
    CourseCategory,
    CourseBundle,
    CourseAnnouncement,
    CourseComment,
    WithdrawalRequest,
)

from .forms import (
    RegisterForm,
    CourseForm,
    CouponApplyForm,
    ReviewForm,
    ChapterForm,
    LessonForm,
    QuestionForm,
    AnswerForm,
    ProfileEditForm,
    AnnouncementForm,
    CommentForm,
)

from .payments import gateway
from . import oauth
from .checkout import place_order, quote_basket, with_display_price
from .transitions import (
    approve_course,
    approve_refund,
    complete_withdrawal,
    fulfill_order,
    reject_course,
    reject_refund,
    reject_withdrawal,
)


def home(request):
    sort = request.GET.get('sort', 'newest')
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()

    qs = Course.objects.filter(is_published=True).select_related('teacher', 'category')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(teacher__username__icontains=q))
    if cat:
        qs = qs.filter(category__name=cat)

    qs = qs.annotate(student_count=Count('enrollment', distinct=True))

    sort_map = {
        'newest': '-created_at',
        'popular': '-student_count',
        'price_asc': 'price',
        'price_desc': '-price',
    }
    if sort not in sort_map:
        sort = 'newest'
    if sort == 'popular':
        qs = qs.order_by('-student_count', '-created_at')
    else:
        qs = qs.order_by(sort_map[sort])

    paginator = Paginator(qs, 8)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 評分：一次查完本頁所有課程，避免每堂課各發一次查詢（遠端 DB 的 N+1 效能殺手）
    def _attach_reviews(courses):
        courses = list(courses)
        ids = [c.id for c in courses]
        stats_map = {
            row['course']: row
            for row in Review.objects.filter(course_id__in=ids)
            .values('course')
            .annotate(avg=Avg('rating'), n=Count('id'))
        }
        for c in courses:
            s = stats_map.get(c.id)
            c.avg_rating = round(s['avg'], 1) if s and s['avg'] else None
            c.review_count = s['n'] if s else 0
        return courses

    _attach_reviews(page_obj.object_list)

    categories = CourseCategory.objects.order_by('name')
    total_students = Enrollment.objects.values('student').distinct().count()
    total_courses = Course.objects.filter(is_published=True).count()
    avg_all = Review.objects.aggregate(a=Avg('rating'))['a']
    avg_all = round(avg_all, 1) if avg_all else 4.8

    def _decorate(qs):
        return _attach_reviews(qs)

    base_pub = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    popular_courses = _decorate(
        base_pub.annotate(sc=Count('enrollment', distinct=True)).order_by('-sc', '-created_at')[:10]
    )
    latest_courses = _decorate(base_pub.order_by('-created_at')[:10])

    now = timezone.now()
    funding_courses = list(
        base_pub.filter(
            is_crowdfunding=True,
            funding_start_date__lte=now,
            funding_end_date__gte=now,
        ).order_by('funding_end_date')[:10]
    )

    return render(request, 'main/home.html', {
        'page_obj': page_obj,
        'sort': sort,
        'q': q,
        'cat': cat,
        'categories': categories,
        'total_students': total_students,
        'total_courses': total_courses,
        'avg_all': avg_all,
        'popular_courses': popular_courses,
        'latest_courses': latest_courses,
        'funding_courses': funding_courses,
        'sort_options': [
            ('newest', '最新'),
            ('popular', '熱門'),
            ('price_asc', '價格低→高'),
            ('price_desc', '價格高→低'),
        ],
    })


def _course_stats_annotations():
    """課程統計（購課數／觀看分鐘／營收／平均評分）的子查詢。

    為什麼用 Subquery 而不是四個 annotate：那些統計各自來自不同的 to-many
    關聯，一起 annotate 會在 JOIN 後產生笛卡爾積，Sum 與 Avg 會被重複計算
    放大。Subquery 各算各的，且整批課程只發一次查詢。

    取代的是「每門課各發四次查詢」的迴圈 —— 在跨網路的共用資料庫上，
    5 門課要 21 次往返、約 2.8 秒。
    """
    def _for(qs, expr, alias):
        return qs.filter(course=OuterRef('pk')).values('course').annotate(
            **{alias: expr}
        ).values(alias)[:1]

    return {
        'purchase_count': Coalesce(
            Subquery(_for(Enrollment.objects.all(), Count('id'), 'n'),
                     output_field=IntegerField()), 0),
        'watch_minutes': Coalesce(
            Subquery(_for(LearningRecord.objects.all(), Sum('minutes'), 's'),
                     output_field=IntegerField()), 0),
        'revenue': Coalesce(
            Subquery(_for(Order.objects.filter(status='paid'), Sum('final_price'), 's'),
                     output_field=IntegerField()), 0),
        'rating': Subquery(
            _for(Review.objects.all(), Avg('rating'), 'a'), output_field=FloatField()),
    }


def _visible_course_or_404(request, course_id):
    """取課程。未上架的只有講師本人、管理員、已購課者看得到。

    回傳 (course, is_preview)。is_preview=True 表示這是未上架課程的預覽 ——
    畫面要標示審核狀態，購買入口一律關閉（見 _purchasable_course_or_404）。

    已購課者也放行，是因為課程可能在購買後才被下架；讓付過錢的人吃 404
    等於沒收他買到的東西。
    """
    course = get_object_or_404(Course, id=course_id)
    if course.is_published:
        return course, False

    user = request.user
    can_preview = user.is_authenticated and (
        course.teacher_id == user.id
        or user.is_superuser
        or Enrollment.objects.filter(student=user, course=course).exists()
    )
    if not can_preview:
        raise Http404('課程不存在或尚未上架')

    return course, True


def _purchasable_course_or_404(request, course_id):
    """取可購買的課程。未上架者一律不可購買 —— 講師與管理員也不行。"""
    course, is_preview = _visible_course_or_404(request, course_id)
    if is_preview:
        raise Http404('課程尚未上架，無法購買')
    return course


def course_detail(request, course_id):
    course, is_preview = _visible_course_or_404(request, course_id)

    already_purchased = False
    can_review = False
    my_review = None
    review_form = None
    is_favorited = False

    if request.user.is_authenticated:
        already_purchased = Enrollment.objects.filter(
            student=request.user,
            course=course
        ).exists()

        is_favorited = Favorite.objects.filter(
            user=request.user,
            course=course
        ).exists()

        if already_purchased:
            can_review = True
            my_review = Review.objects.filter(
                user=request.user,
                course=course
            ).first()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        if not already_purchased:
            return redirect('course_detail', course_id=course.id)

        if my_review:
            review_form = ReviewForm(request.POST, instance=my_review)
        else:
            review_form = ReviewForm(request.POST)

        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.user = request.user
            review.course = course
            review.save()

            return redirect('course_detail', course_id=course.id)

    else:
        if my_review:
            review_form = ReviewForm(instance=my_review)
        else:
            review_form = ReviewForm()

    chapters = course.chapters.prefetch_related('lessons').all()

    reviews = Review.objects.filter(
        course=course
    ).select_related('user').order_by('-created_at')

    average_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    if average_rating:
        average_rating = round(average_rating, 1)

    review_count = reviews.count()

    # A7：課程問答
    questions = CourseQuestion.objects.filter(
        course=course
    ).select_related('user').prefetch_related('answers__user').order_by('-created_at')

    is_course_teacher = request.user.is_authenticated and course.teacher_id == request.user.id

    # 課程統計（銷售頁用）
    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    total_minutes = CourseLesson.objects.filter(chapter__course=course).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    student_count = Enrollment.objects.filter(course=course).count()

    return render(request, 'main/course_detail.html', {
        'course': course,
        'already_purchased': already_purchased,
        'chapters': chapters,
        'reviews': reviews,
        'average_rating': average_rating,
        'review_count': review_count,
        'can_review': can_review,
        'my_review': my_review,
        'review_form': review_form,
        'is_favorited': is_favorited,
        'questions': questions,
        'question_form': QuestionForm(),
        'answer_form': AnswerForm(),
        'is_course_teacher': is_course_teacher,
        'total_lessons': total_lessons,
        'total_minutes': total_minutes,
        'student_count': student_count,
        'is_preview': is_preview,
    })


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            Profile.objects.create(
                user=user,
                role=form.cleaned_data['role']
            )

            return redirect('register_success')
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {
        'form': form
    })


def register_success(request):
    return render(request, 'main/register_success.html')


def login_view(request):
    error_message = None

    if request.method == 'POST':
        login_input = request.POST.get('username')
        password = request.POST.get('password')

        if '@' in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                username = user_obj.username
            except User.DoesNotExist:
                username = login_input
        else:
            username = login_input

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            if user.is_superuser:
                return redirect('/admin/')

            try:
                profile = user.profile

                if profile.role == 'teacher':
                    return redirect('teacher_dashboard')
                elif profile.role == 'student':
                    return redirect('student_dashboard')
                else:
                    return redirect('home')

            except Profile.DoesNotExist:
                return redirect('home')

        else:
            error_message = '帳號 / Email 或密碼錯誤。'

    return render(request, 'main/login.html', {
        'error_message': error_message
    })


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    total_minutes = LearningRecord.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    purchased_count = Enrollment.objects.filter(
        student=request.user
    ).count()

    return render(request, 'main/profile.html', {
        'profile': profile,
        'total_minutes': total_minutes,
        'purchased_count': purchased_count,
    })


@login_required
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=profile, user=request.user)

    return render(request, 'main/edit_profile.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def student_dashboard(request):
    try:
        profile = request.user.profile

        if profile.role != 'student':
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    total_minutes = LearningRecord.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    purchased_count = Enrollment.objects.filter(
        student=request.user
    ).count()

    return render(request, 'main/student_dashboard.html', {
        'total_minutes': total_minutes,
        'purchased_count': purchased_count,
    })


@login_required
def teacher_dashboard(request):
    try:
        profile = request.user.profile

        if profile.role != 'teacher':
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    # 一次查完所有統計，不再逐課發四次查詢（見 _course_stats_annotations）
    teacher_courses = Course.objects.filter(
        teacher=request.user
    ).select_related('category').annotate(**_course_stats_annotations())

    course_data = [
        {
            'course': course,
            'purchase_count': course.purchase_count,
            'total_watch_minutes': course.watch_minutes,
            'total_revenue': course.revenue,
            'average_rating': round(course.rating, 1) if course.rating else None,
        }
        for course in teacher_courses
    ]

    return render(request, 'main/teacher_dashboard.html', {
        'course_data': course_data
    })


@login_required
def my_courses(request):
    try:
        request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    # 觀看分鐘與課程總長用子查詢一次算完，不再逐筆發查詢
    enrollments = list(
        Enrollment.objects.filter(student=request.user)
        .select_related('course', 'course__teacher', 'course__category')
        .annotate(
            watch_minutes=Coalesce(
                Subquery(
                    LearningRecord.objects
                    .filter(user=request.user, course=OuterRef('course'))
                    .values('course').annotate(s=Sum('minutes')).values('s')[:1],
                    output_field=IntegerField(),
                ), 0),
            course_total_minutes=Coalesce(
                Subquery(
                    CourseLesson.objects
                    .filter(chapter__course=OuterRef('course'))
                    .values('chapter__course')
                    .annotate(s=Sum('duration_minutes')).values('s')[:1],
                    output_field=IntegerField(),
                ), 0),
        )
    )

    # 退款整合進我的課程：訂單與退款狀態各用一次查詢批次取回，
    # 依 id 遞增覆蓋 → 每門課留下的就是最新一筆。
    course_ids = [e.course_id for e in enrollments]
    orders_by_course = {
        o.course_id: o
        for o in Order.objects.filter(
            user=request.user, course_id__in=course_ids, status='paid'
        ).order_by('id')
    }
    refunds_by_order = {
        r.order_id: r
        for r in Refund.objects.filter(
            order_id__in=[o.id for o in orders_by_course.values()]
        ).order_by('id')
    }

    for enrollment in enrollments:
        total = enrollment.course_total_minutes
        enrollment.progress = (
            int(min(enrollment.watch_minutes, total) / total * 100) if total > 0 else 0
        )
        order = orders_by_course.get(enrollment.course_id)
        enrollment.order = order
        enrollment.refund = refunds_by_order.get(order.id) if order else None

    total_minutes = LearningRecord.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    return render(request, 'main/my_courses.html', {
        'enrollments': enrollments,
        'total_minutes': total_minutes,
    })


@login_required
def checkout(request, course_id):
    course = _purchasable_course_or_404(request, course_id)

    try:
        request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    if Enrollment.objects.filter(
        student=request.user,
        course=course
    ).exists():
        return redirect('course_detail', course_id=course.id)

    form = CouponApplyForm(request.POST or None)

    action = request.POST.get('action', 'buy') if request.method == 'POST' else ''
    selected_code = request.POST.get('coupon_code', '').strip() if request.method == 'POST' else ''

    # 定價與下單一律走 checkout module：單課只是「只有一項的購物籃」，
    # 因此和購物車結帳算出完全相同的價格（含促銷）。詞彙見 CONTEXT.md。
    quote = quote_basket(request.user, [course], selected_code)
    if quote.is_empty:
        # 上面的已購課檢查與這裡之間有購買發生（並行送出兩次表單）
        return redirect('course_detail', course_id=course.id)

    error_message = quote.coupon_error
    success_message = (
        f'優惠券已套用，折抵 NT$ {quote.coupon_total}。' if quote.coupon_total > 0 else None
    )

    # 只有按「確認購買」且沒有錯誤時才成立「待付款」訂單，導向付款頁；
    # 按「套用優惠券」只重新整理頁面顯示折扣預覽。付款完成後才會開通課程。
    if action == 'buy' and not error_message:
        order = place_order(request.user, quote)
        return redirect('payment', order_id=order.id)

    # A4：帶出使用者可用的優惠券供選擇
    now = timezone.now()
    my_coupons = UserCoupon.objects.filter(
        user=request.user, status='unused'
    ).select_related('coupon').filter(
        coupon__is_active=True,
        coupon__start_date__lte=now,
        coupon__end_date__gte=now,
    )

    return render(request, 'main/checkout.html', {
        'course': course,
        'form': form,
        'list_price': quote.list_total,
        'original_price': quote.subtotal,
        'promo_discount': quote.promo_total,
        'discount_amount': quote.coupon_total,
        'final_price': quote.total,
        'error_message': error_message,
        'success_message': success_message,
        'my_coupons': my_coupons,
        'selected_code': selected_code,
    })


@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    # 未付款完成的訂單導回付款頁
    if order.status != 'paid':
        return redirect('payment', order_id=order.id)

    payment_obj = order.payments.order_by('-id').first()

    return render(request, 'main/order_success.html', {
        'order': order,
        'payment': payment_obj,
        'items': order.items.select_related('course').all(),
    })


@login_required
def buy_course(request, course_id):
    return redirect('checkout', course_id=course_id)


@login_required
def purchase_success(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    return render(request, 'main/purchase_success.html', {
        'course': course
    })


@login_required
def watch_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    has_purchased = Enrollment.objects.filter(
        student=request.user,
        course=course
    ).exists()

    if not has_purchased and course.teacher_id != request.user.id:
        return redirect('course_detail', course_id=course.id)

    # 導向課程第一個單元的播放頁
    first_lesson = CourseLesson.objects.filter(
        chapter__course=course
    ).order_by('chapter__sort_order', 'sort_order').first()

    if first_lesson:
        return redirect('watch_lesson', lesson_id=first_lesson.id)

    return redirect('course_detail', course_id=course.id)


@login_required
def watch_lesson(request, lesson_id):
    lesson = get_object_or_404(
        CourseLesson.objects.select_related('chapter__course'), id=lesson_id
    )
    course = lesson.chapter.course

    enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    is_teacher = course.teacher_id == request.user.id

    # 免費試看單元任何登入者可看；其餘需購買或為講師
    if not (enrolled or is_teacher or lesson.is_free_preview):
        return redirect('course_detail', course_id=course.id)

    # 側欄：所有章節/單元 + 完成狀態
    chapters = course.chapters.prefetch_related('lessons').all()
    completed_ids = set(
        LearningRecord.objects.filter(user=request.user, course=course)
        .exclude(lesson=None).values_list('lesson_id', flat=True)
    )

    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    done_count = len(completed_ids)
    progress = int(done_count / total_lessons * 100) if total_lessons else 0

    is_completed = lesson.id in completed_ids

    # 本單元的累積進度與續看位置
    prog = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
    lesson_percent = prog.percent() if prog else 0
    resume_position = 0
    if prog:
        # 尚未看到接近結尾才續看，否則從頭
        if prog.duration and prog.last_position < prog.duration - 3:
            resume_position = prog.last_position

    return render(request, 'main/watch_lesson.html', {
        'course': course,
        'lesson': lesson,
        'chapters': chapters,
        'completed_ids': completed_ids,
        'progress': progress,
        'done_count': done_count,
        'total_lessons': total_lessons,
        'is_completed': is_completed,
        'can_record': enrolled or is_teacher,
        'lesson_percent': lesson_percent,
        'resume_position': resume_position,
    })


@login_required
def save_progress(request, lesson_id):
    """AJAX：累積觀看秒數 + 記錄續看位置；達 60% 自動標記完成。"""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    lesson = get_object_or_404(
        CourseLesson.objects.select_related('chapter__course'), id=lesson_id
    )
    course = lesson.chapter.course
    enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    is_teacher = course.teacher_id == request.user.id
    if not (enrolled or is_teacher):
        return JsonResponse({'ok': False}, status=403)

    prog, _ = LessonProgress.objects.get_or_create(
        user=request.user, lesson=lesson, defaults={'course': course}
    )

    try:
        duration = int(float(request.POST.get('duration', 0) or 0))
        position = int(float(request.POST.get('position', 0) or 0))
    except (TypeError, ValueError):
        duration, position = 0, 0

    new_secs = [
        int(s) for s in request.POST.get('seconds', '').split(',')
        if s.strip().isdigit()
    ]

    if duration > 0:
        prog.duration = duration

    # 合併新看過的秒數進 bitmap（快轉跳過的秒不會被加入）
    n = max(len(prog.watched_map), prog.duration, (max(new_secs) + 1 if new_secs else 0))
    bitmap = list(prog.watched_map.ljust(n, '0'))
    for s in new_secs:
        if 0 <= s < len(bitmap):
            bitmap[s] = '1'
    prog.watched_map = ''.join(bitmap)
    prog.watched_seconds = prog.watched_map.count('1')
    if position > 0:
        prog.last_position = position

    completed_now = False
    if prog.duration > 0 and prog.watched_seconds / prog.duration >= 0.6 and not prog.is_completed:
        prog.is_completed = True
        completed_now = True

    prog.save()

    if completed_now:
        minutes = lesson.duration_minutes or max(1, round(prog.duration / 60))
        LearningRecord.objects.get_or_create(
            user=request.user, course=course, lesson=lesson,
            defaults={'minutes': minutes}
        )

    return JsonResponse({
        'ok': True,
        'progress': prog.percent(),
        'completed': prog.is_completed,
    })


@login_required
def create_course(request):
    try:
        profile = request.user.profile

        if profile.role != 'teacher':
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)

        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.is_published = False  # A8：送審前不上架
            course.save()

            CourseAudit.objects.create(course=course, status='pending')

            Notification.objects.create(
                user=request.user,
                title='課程已送審',
                content=f'你的課程「{course.title}」已送出審核，通過後才會上架。'
            )

            return redirect('teacher_dashboard')

    else:
        form = CourseForm()

    return render(request, 'main/create_course.html', {
        'form': form
    })


@login_required
def edit_course(request, course_id):
    try:
        profile = request.user.profile

        if profile.role != 'teacher':
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    course = get_object_or_404(
        Course,
        id=course_id,
        teacher=request.user
    )

    if request.method == 'POST':
        form = CourseForm(
            request.POST,
            request.FILES,
            instance=course
        )

        if form.is_valid():
            form.save()
            return redirect('teacher_dashboard')

    else:
        form = CourseForm(instance=course)

    return render(request, 'main/edit_course.html', {
        'form': form,
        'course': course
    })


@login_required
def delete_course(request, course_id):
    try:
        profile = request.user.profile

        if profile.role != 'teacher':
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    course = get_object_or_404(
        Course,
        id=course_id,
        teacher=request.user
    )

    if request.method == 'POST':
        course.delete()
        return redirect('teacher_dashboard')

    return render(request, 'main/delete_course.html', {
        'course': course
    })


@login_required
def student_analytics(request):
    try:
        profile = request.user.profile
        if profile.role != 'student':
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    total_minutes = LearningRecord.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    purchased_count = Enrollment.objects.filter(
        student=request.user
    ).count()

    course_minutes_data = LearningRecord.objects.filter(
        user=request.user
    ).values(
        'course__title'
    ).annotate(
        total=Sum('minutes')
    ).order_by('-total')

    course_labels = [item['course__title'] for item in course_minutes_data]
    course_minutes = [item['total'] for item in course_minutes_data]

    recent_records = LearningRecord.objects.filter(
        user=request.user
    ).select_related(
        'course',
        'lesson'
    ).order_by('-watched_at')[:10]

    return render(request, 'main/student_analytics.html', {
        'total_minutes': total_minutes,
        'purchased_count': purchased_count,
        'course_labels_json': json.dumps(course_labels, ensure_ascii=False),
        'course_minutes_json': json.dumps(course_minutes),
        'recent_records': recent_records,
    })


@login_required
def teacher_analytics(request):
    try:
        profile = request.user.profile
        if profile.role != 'teacher':
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    # 逐課統計一次查完（見 _course_stats_annotations）
    teacher_courses = Course.objects.filter(
        teacher=request.user
    ).annotate(**_course_stats_annotations())

    total_revenue = Order.objects.filter(
        course__teacher=request.user,
        status='paid'
    ).aggregate(
        total=Sum('final_price')
    )['total'] or 0

    total_purchase_count = Enrollment.objects.filter(
        course__teacher=request.user
    ).count()

    total_watch_minutes = LearningRecord.objects.filter(
        course__teacher=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    course_labels = []
    purchase_counts = []
    revenue_data = []
    watch_minutes_data = []
    rating_data = []

    for course in teacher_courses:
        course_labels.append(course.title)
        purchase_counts.append(course.purchase_count)
        revenue_data.append(course.revenue)
        watch_minutes_data.append(course.watch_minutes)
        rating_data.append(round(course.rating, 1) if course.rating else 0)

    return render(request, 'main/teacher_analytics.html', {
        'total_revenue': total_revenue,
        'total_purchase_count': total_purchase_count,
        'total_watch_minutes': total_watch_minutes,
        'course_labels_json': json.dumps(course_labels, ensure_ascii=False),
        'purchase_counts_json': json.dumps(purchase_counts),
        'revenue_data_json': json.dumps(revenue_data),
        'watch_minutes_data_json': json.dumps(watch_minutes_data),
        'rating_data_json': json.dumps(rating_data),
    })
@login_required
def export_data_page(request):
    if not request.user.is_superuser:
        return redirect('home')

    export_groups = [
        ('核心資料', [
            ('課程資料 courses.csv', '課程名稱、講師、分類、難度、價格與建立時間。', reverse('export_courses_csv')),
            ('購課紀錄 enrollments.csv', '學生購買課程紀錄，可分析課程銷售與購買趨勢。', reverse('export_enrollments_csv')),
            ('學習紀錄 learning_records.csv', '觀看分鐘數與觀看時間，可分析學習時數。', reverse('export_learning_records_csv')),
            ('使用者角色 profiles.csv', '使用者帳號、Email 與角色。', reverse('export_profiles_csv')),
        ]),
        ('交易與營收資料', [
            ('訂單資料 orders.csv', '原價、折扣、實付金額與訂單狀態。', reverse('export_orders_csv')),
            ('訂單明細 order_items.csv', '每筆訂單購買的課程明細。', reverse('export_order_items_csv')),
            ('付款紀錄 payments.csv', '付款方式、付款金額、付款狀態與交易編號。', reverse('export_payments_csv')),
            ('優惠券使用 coupon_usage.csv', '優惠碼、使用者、訂單與折扣金額。', reverse('export_coupon_usage_csv')),
        ]),
        ('課程內容與評價資料', [
            ('課程評價 reviews.csv', '學生評分與評論內容，可分析課程滿意度。', reverse('export_reviews_csv')),
            ('課程單元 course_lessons.csv', '課程章節、單元、影片分鐘數與免費試看狀態。', reverse('export_course_lessons_csv')),
        ]),
    ]

    return render(request, 'main/export_data.html', {
        'export_groups': export_groups,
    })


@login_required
def platform_analytics(request):
    if not request.user.is_superuser:
        return redirect('home')

    from django.db.models.functions import TruncDate

    paid_orders = Order.objects.filter(status='paid')
    total_revenue = paid_orders.aggregate(s=Sum('final_price'))['s'] or 0
    total_students = Enrollment.objects.values('student').distinct().count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_courses = Course.objects.count()
    avg_rating = Review.objects.aggregate(a=Avg('rating'))['a']
    avg_rating = round(avg_rating, 1) if avg_rating else None
    pending_refunds = Refund.objects.filter(status='pending').count()
    pending_audits = CourseAudit.objects.filter(status='pending').count()
    total_discount = CouponUsage.objects.aggregate(s=Sum('discount_amount'))['s'] or 0

    # 近 30 天營收趨勢
    since = timezone.now() - timezone.timedelta(days=29)
    daily = (
        paid_orders.filter(created_at__gte=since)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('final_price'))
        .order_by('day')
    )
    daily_map = {d['day']: d['revenue'] for d in daily}
    revenue_labels = []
    revenue_series = []
    for i in range(30):
        day = (since + timezone.timedelta(days=i)).date()
        revenue_labels.append(day.strftime('%m/%d'))
        revenue_series.append(daily_map.get(day, 0))

    # 熱銷課程 Top 5（依訂單明細原價加總，涵蓋單課與購物車多課訂單）
    top_courses = (
        OrderItem.objects.filter(order__status='paid')
        .values('course__title')
        .annotate(gross=Sum('price'), purchases=Count('id'))
        .order_by('-gross')[:5]
    )
    top_course_labels = [t['course__title'] or '（課程已刪除）' for t in top_courses]
    top_course_revenue = [t['gross'] for t in top_courses]

    # 課程分類分布
    cat_dist = (
        Course.objects.filter(is_published=True)
        .values('category__name')
        .annotate(n=Count('id'))
        .order_by('-n')
    )
    cat_labels = [c['category__name'] or '未分類' for c in cat_dist]
    cat_counts = [c['n'] for c in cat_dist]

    # 付款方式分布
    method_dist = (
        Payment.objects.filter(status='paid')
        .values('method')
        .annotate(n=Count('id'))
        .order_by('-n')
    )
    method_display = dict(Payment.PAYMENT_METHOD_CHOICES)
    method_labels = [method_display.get(m['method'], m['method']) for m in method_dist]
    method_counts = [m['n'] for m in method_dist]

    # 訂單狀態分布
    status_dist = Order.objects.values('status').annotate(n=Count('id')).order_by('-n')
    status_display = dict(Order.STATUS_CHOICES)
    status_labels = [status_display.get(s['status'], s['status']) for s in status_dist]
    status_counts = [s['n'] for s in status_dist]

    return render(request, 'main/platform_analytics.html', {
        'total_revenue': total_revenue,
        'total_students': total_students,
        'published_courses': published_courses,
        'total_courses': total_courses,
        'avg_rating': avg_rating,
        'pending_refunds': pending_refunds,
        'pending_audits': pending_audits,
        'total_discount': total_discount,
        'revenue_labels_json': json.dumps(revenue_labels),
        'revenue_series_json': json.dumps(revenue_series),
        'top_course_labels_json': json.dumps(top_course_labels, ensure_ascii=False),
        'top_course_revenue_json': json.dumps(top_course_revenue),
        'cat_labels_json': json.dumps(cat_labels, ensure_ascii=False),
        'cat_counts_json': json.dumps(cat_counts),
        'method_labels_json': json.dumps(method_labels, ensure_ascii=False),
        'method_counts_json': json.dumps(method_counts),
        'status_labels_json': json.dumps(status_labels, ensure_ascii=False),
        'status_counts_json': json.dumps(status_counts),
    })


def create_csv_response(filename):
    """\u5efa\u7acb\u5e36 UTF-8 BOM \u7684 CSV response\uff0cExcel/LibreOffice \u958b\u555f\u6642\u6703\u81ea\u52d5\u5224\u65b7\u7de8\u78bc\u3001
    \u4e0d\u8df3\u51fa\u532f\u5165\u7cbe\u9748\uff0c\u4e2d\u6587\u4e5f\u4e0d\u6703\u4e82\u78bc\u3002

    \u9019\u88e1\u523b\u610f\u628a charset \u8a2d\u70ba utf-8\uff08\u4e0d\u662f utf-8-sig\uff09\u518d\u624b\u52d5\u5beb\u4e00\u6b21 BOM \u2014\u2014 HttpResponse
    \u662f\u9010\u6b21 write() \u500b\u5225\u7de8\u78bc\uff08\u4e0d\u662f\u7528\u540c\u4e00\u689d\u4e32\u6d41\u7d2f\u52a0\uff09\uff0c\u82e5 charset \u8a2d\u6210 utf-8-sig\uff0c
    \u4e4b\u5f8c csv.writer \u6bcf\u547c\u53eb\u4e00\u6b21 writerow() \u90fd\u6703\u5404\u81ea\u88ab\u52a0\u4e0a\u4e00\u500b BOM\uff0c
    \u6574\u4efd CSV \u6bcf\u4e00\u884c\u524d\u9762\u90fd\u6703\u591a\u51fa\u4e00\u500b\u770b\u4e0d\u898b\u7684 BOM \u5b57\u5143\uff0cExcel \u958b\u51fa\u4f86\u6bcf\u4e00\u5217\u90fd\u6703\u932f\u4f4d\u3002
    BOM \u53ea\u9700\u8981\u51fa\u73fe\u5728\u6a94\u6848\u6700\u958b\u982d\u4e00\u6b21\uff0c\u6240\u4ee5\u6539\u6210\u624b\u52d5\u53ea\u5beb\u4e00\u6b21\u3002
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    return response


@login_required
def export_courses_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('courses.csv')
    writer = csv.writer(response)

    writer.writerow([
        'course_id',
        'course_title',
        'teacher_username',
        'teacher_email',
        'category',
        'level',
        'price',
        'description',
        'is_published',
        'created_at',
    ])

    courses = Course.objects.select_related(
        'teacher',
        'category'
    ).all()

    for course in courses:
        writer.writerow([
            course.id,
            course.title,
            course.teacher.username,
            course.teacher.email,
            course.category.name if course.category else '',
            course.get_level_display(),
            course.price,
            course.description,
            course.is_published,
            course.created_at,
        ])

    return response


@login_required
def export_enrollments_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('enrollments.csv')
    writer = csv.writer(response)

    writer.writerow([
        'enrollment_id',
        'student_username',
        'student_email',
        'course_id',
        'course_title',
        'teacher_username',
        'purchased_at',
    ])

    enrollments = Enrollment.objects.select_related(
        'student',
        'course',
        'course__teacher'
    ).all()

    for enrollment in enrollments:
        writer.writerow([
            enrollment.id,
            enrollment.student.username,
            enrollment.student.email,
            enrollment.course.id,
            enrollment.course.title,
            enrollment.course.teacher.username,
            enrollment.purchased_at,
        ])

    return response


@login_required
def export_learning_records_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('learning_records.csv')
    writer = csv.writer(response)

    writer.writerow([
        'record_id',
        'username',
        'email',
        'course_id',
        'course_title',
        'teacher_username',
        'lesson_title',
        'minutes',
        'watched_at',
    ])

    records = LearningRecord.objects.select_related(
        'user',
        'course',
        'course__teacher',
        'lesson'
    ).all()

    for record in records:
        writer.writerow([
            record.id,
            record.user.username,
            record.user.email,
            record.course.id,
            record.course.title,
            record.course.teacher.username,
            record.lesson.title if record.lesson else '',
            record.minutes,
            record.watched_at,
        ])

    return response


@login_required
def export_profiles_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('profiles.csv')
    writer = csv.writer(response)

    writer.writerow([
        'profile_id',
        'username',
        'email',
        'role',
        'role_display',
    ])

    profiles = Profile.objects.select_related('user').all()

    for profile in profiles:
        writer.writerow([
            profile.id,
            profile.user.username,
            profile.user.email,
            profile.role,
            profile.get_role_display(),
        ])

    return response

@login_required
def export_orders_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('orders.csv')
    writer = csv.writer(response)

    writer.writerow([
        'order_id',
        'username',
        'email',
        'course_id',
        'course_title',
        'coupon_code',
        'original_price',
        'discount_amount',
        'final_price',
        'status',
        'created_at',
    ])

    orders = Order.objects.select_related(
        'user',
        'course',
        'coupon'
    ).all()

    for order in orders:
        writer.writerow([
            order.id,
            order.user.username,
            order.user.email,
            order.course.id if order.course else '',
            order.course.title if order.course else '',
            order.coupon.code if order.coupon else '',
            order.original_price,
            order.discount_amount,
            order.final_price,
            order.status,
            order.created_at,
        ])

    return response


@login_required
def export_order_items_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('order_items.csv')
    writer = csv.writer(response)

    writer.writerow([
        'order_item_id',
        'order_id',
        'username',
        'course_id',
        'course_title',
        'teacher_username',
        'price',
    ])

    items = OrderItem.objects.select_related(
        'order',
        'order__user',
        'course',
        'course__teacher'
    ).all()

    for item in items:
        writer.writerow([
            item.id,
            item.order.id,
            item.order.user.username,
            item.course.id,
            item.course.title,
            item.course.teacher.username,
            item.price,
        ])

    return response


@login_required
def export_payments_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('payments.csv')
    writer = csv.writer(response)

    writer.writerow([
        'payment_id',
        'order_id',
        'username',
        'method',
        'amount',
        'status',
        'transaction_no',
        'paid_at',
        'created_at',
    ])

    payments = Payment.objects.select_related(
        'order',
        'order__user'
    ).all()

    for payment in payments:
        writer.writerow([
            payment.id,
            payment.order.id,
            payment.order.user.username,
            payment.method,
            payment.amount,
            payment.status,
            payment.transaction_no,
            payment.paid_at,
            payment.created_at,
        ])

    return response


@login_required
def export_coupon_usage_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('coupon_usage.csv')
    writer = csv.writer(response)

    writer.writerow([
        'coupon_usage_id',
        'username',
        'coupon_code',
        'coupon_name',
        'order_id',
        'discount_amount',
        'used_at',
    ])

    usages = CouponUsage.objects.select_related(
        'user',
        'coupon',
        'order'
    ).all()

    for usage in usages:
        writer.writerow([
            usage.id,
            usage.user.username,
            usage.coupon.code,
            usage.coupon.name,
            usage.order.id,
            usage.discount_amount,
            usage.used_at,
        ])

    return response


@login_required
def export_reviews_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('reviews.csv')
    writer = csv.writer(response)

    writer.writerow([
        'review_id',
        'username',
        'email',
        'course_id',
        'course_title',
        'teacher_username',
        'rating',
        'comment',
        'created_at',
        'updated_at',
    ])

    reviews = Review.objects.select_related(
        'user',
        'course',
        'course__teacher'
    ).all()

    for review in reviews:
        writer.writerow([
            review.id,
            review.user.username,
            review.user.email,
            review.course.id,
            review.course.title,
            review.course.teacher.username,
            review.rating,
            review.comment,
            review.created_at,
            review.updated_at,
        ])

    return response


@login_required
def export_course_lessons_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    response = create_csv_response('course_lessons.csv')
    writer = csv.writer(response)

    writer.writerow([
        'lesson_id',
        'course_id',
        'course_title',
        'chapter_id',
        'chapter_title',
        'lesson_title',
        'duration_minutes',
        'is_free_preview',
        'sort_order',
        'created_at',
    ])

    lessons = CourseLesson.objects.select_related(
        'chapter',
        'chapter__course'
    ).all()

    for lesson in lessons:
        writer.writerow([
            lesson.id,
            lesson.chapter.course.id,
            lesson.chapter.course.title,
            lesson.chapter.id,
            lesson.chapter.title,
            lesson.title,
            lesson.duration_minutes,
            lesson.is_free_preview,
            lesson.sort_order,
            lesson.created_at,
        ])

    return response


# =========================
# 購物車 Cart
# =========================

@login_required
def add_to_cart(request, course_id):
    # 改資料庫狀態的動作只接受 POST —— GET 不受 CSRF middleware 保護，
    # 一個 <img src> 或預抓就能代替使用者送出。畫面本來就是 POST 表單。
    if request.method != 'POST':
        return redirect('course_detail', course_id=course_id)

    course = _purchasable_course_or_404(request, course_id)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', course_id=course.id)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    CartItem.objects.get_or_create(cart=cart, course=course)

    return redirect('view_cart')


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = list(cart.items.select_related('course', 'course__teacher').all())
    # 顯示價含促銷，才會和結帳實際收的錢一致（批次計算，不逐課查詢）
    with_display_price([item.course for item in items])
    total = sum(item.course.display_price for item in items)

    # 優惠券整合進購物車：可領取 + 我的優惠券
    now = timezone.now()
    available_coupons = Coupon.objects.filter(
        is_active=True, start_date__lte=now, end_date__gte=now
    ).order_by('-created_at')
    claimed_ids = set(
        UserCoupon.objects.filter(user=request.user).values_list('coupon_id', flat=True)
    )
    my_coupons = UserCoupon.objects.filter(
        user=request.user
    ).select_related('coupon').order_by('-received_at')

    return render(request, 'main/cart.html', {
        'items': items,
        'total': total,
        'available_coupons': available_coupons,
        'claimed_ids': claimed_ids,
        'my_coupons': my_coupons,
    })


@login_required
def remove_from_cart(request, item_id):
    if request.method != 'POST':
        return redirect('view_cart')

    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('view_cart')


@login_required
def cart_checkout(request):
    # 成立訂單會改資料庫狀態，只接受 POST（cart.html 已經是 POST 表單）。
    # 先前沒有這道檢查，一個 GET（含瀏覽器預抓、重新整理）就會多一張訂單。
    if request.method != 'POST':
        return redirect('view_cart')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    courses = [item.course for item in cart.items.select_related('course').all()]

    # 定價與下單一律走 checkout module；已購課過濾、促銷、券分攤都在裡面。
    quote = quote_basket(request.user, courses, request.POST.get('coupon_code', ''))
    if quote.is_empty:
        return redirect('view_cart')

    order = place_order(request.user, quote)
    cart.items.all().delete()

    return redirect('payment', order_id=order.id)


# =========================
# 模擬金流 付款流程
# =========================

def _mark_payment_paid(payment, result):
    payment.status = 'paid'
    payment.paid_at = timezone.now()
    if result.transaction_no:
        payment.transaction_no = result.transaction_no
    payment.save()


@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'paid':
        return redirect('order_success', order_id=order.id)

    # place_order 是原子性的，新訂單一定帶著 Payment。這個 get_or_create 只為了
    # 修補在該修正之前建立、可能沒有 Payment 的舊待付款訂單。
    payment_obj, _ = Payment.objects.get_or_create(
        order=order,
        defaults={'amount': order.final_price, 'status': 'pending', 'method': 'mock'}
    )
    if payment_obj.amount != order.final_price:
        payment_obj.amount = order.final_price
        payment_obj.save()

    method = ''
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')
        method = request.POST.get('method', '')

        if action == 'select':
            # 選擇付款方式 → 準備該方式的付款資訊
            if method == 'atm':
                gateway.create_atm(payment_obj)
            elif method == 'cvs':
                gateway.create_cvs(payment_obj)
            elif method == 'credit_card':
                payment_obj.method = 'credit_card'
                payment_obj.status = 'pending'
                payment_obj.save()

        elif action == 'pay_card':
            card = {
                'number': request.POST.get('card_number', ''),
                'expiry': request.POST.get('card_expiry', ''),
                'cvc': request.POST.get('card_cvc', ''),
                'name': request.POST.get('card_name', ''),
            }
            result = gateway.charge_credit_card(payment_obj, card)
            if result.success:
                _mark_payment_paid(payment_obj, result)
                fulfill_order(order)
                return redirect('order_success', order_id=order.id)
            error = result.message
            method = 'credit_card'

        elif action == 'confirm_offline':
            # 使用者回報已完成 ATM 轉帳 / 超商繳費（模擬銀行/超商回拋）
            result = gateway.confirm_offline(payment_obj)
            if result.success:
                _mark_payment_paid(payment_obj, result)
                fulfill_order(order)
                return redirect('order_success', order_id=order.id)
            error = result.message
            method = payment_obj.method

    return render(request, 'main/payment.html', {
        'order': order,
        'payment': payment_obj,
        'items': order.items.select_related('course').all(),
        'method': method,
        'error': error,
    })


# =========================
# 收藏 Favorite
# =========================

@login_required
def toggle_favorite(request, course_id):
    if request.method != 'POST':
        return redirect('my_favorites')

    course = get_object_or_404(Course, id=course_id)
    favorite = Favorite.objects.filter(user=request.user, course=course).first()

    if favorite:
        favorite.delete()
    else:
        Favorite.objects.create(user=request.user, course=course)

    # next 是使用者可控的輸入：未經驗證就 redirect 等於開放轉址，
    # 可被拿來把人導去釣魚站再假裝是本站流程。
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect('my_favorites')


@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related('course', 'course__teacher', 'course__category').order_by('-created_at')

    return render(request, 'main/favorites.html', {
        'favorites': favorites,
    })


# =========================
# 退款 Refund
# =========================

@login_required
def request_refund(request, order_id):
    order = get_object_or_404(
        Order, id=order_id, user=request.user, status='paid'
    )

    existing = Refund.objects.filter(
        order=order, status__in=['pending', 'approved']
    ).first()

    if request.method == 'POST' and not existing:
        reason = request.POST.get('reason', '').strip() or '未填寫原因'
        Refund.objects.create(
            order=order,
            user=request.user,
            amount=order.final_price,
            reason=reason,
            status='pending'
        )
        Notification.objects.create(
            user=request.user,
            title='退款申請已送出',
            content=f'訂單 #{order.id} 的退款申請已送出，等待審核。'
        )
        return redirect('my_courses')

    return render(request, 'main/request_refund.html', {
        'order': order,
        'existing': existing,
    })


@login_required
def my_refunds(request):
    # 退款已整合進「我的課程」，舊網址轉址過去
    return redirect('my_courses')


# =========================
# 優惠券領取 UserCoupon
# =========================

@login_required
def coupon_list(request):
    # 優惠券領取已整合進「購物車」，舊網址轉址過去
    return redirect('view_cart')


@login_required
def claim_coupon(request, coupon_id):
    if request.method != 'POST':
        return redirect('view_cart')

    coupon = get_object_or_404(Coupon, id=coupon_id)

    if coupon.is_valid_now():
        UserCoupon.objects.get_or_create(
            user=request.user,
            coupon=coupon,
            defaults={'status': 'unused'}
        )

    return redirect('view_cart')


@login_required
def my_coupons(request):
    # 優惠券管理已整合進「購物車」，舊網址轉址過去
    return redirect('view_cart')


# =========================
# A2 章節 / 單元管理（老師）
# =========================

def _require_course_teacher(request, course_id):
    """回傳 (course, None) 或 (None, redirect)。只有課程講師本人可管理。"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return None, redirect('home')

    if profile.role != 'teacher':
        return None, redirect('home')

    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    return course, None


@login_required
def manage_content(request, course_id):
    course, redirect_resp = _require_course_teacher(request, course_id)
    if redirect_resp:
        return redirect_resp

    chapters = course.chapters.prefetch_related('lessons').all()

    return render(request, 'main/manage_content.html', {
        'course': course,
        'chapters': chapters,
        'chapter_form': ChapterForm(),
        'lesson_form': LessonForm(),
    })


@login_required
def add_chapter(request, course_id):
    course, redirect_resp = _require_course_teacher(request, course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.course = course
            chapter.save()

    return redirect('manage_content', course_id=course.id)


@login_required
def edit_chapter(request, chapter_id):
    chapter = get_object_or_404(CourseChapter, id=chapter_id)
    course, redirect_resp = _require_course_teacher(request, chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            return redirect('manage_content', course_id=course.id)
    else:
        form = ChapterForm(instance=chapter)

    return render(request, 'main/edit_chapter.html', {
        'form': form,
        'chapter': chapter,
        'course': course,
    })


@login_required
def delete_chapter(request, chapter_id):
    chapter = get_object_or_404(CourseChapter, id=chapter_id)
    course, redirect_resp = _require_course_teacher(request, chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        chapter.delete()

    return redirect('manage_content', course_id=course.id)


def _autoset_lesson_duration(lesson):
    """上傳影片檔後自動偵測時長，寫回 duration_minutes（老師免手動輸入）。"""
    if not lesson.video_file:
        return
    try:
        from .videoutils import detect_duration_minutes
        minutes = detect_duration_minutes(lesson.video_file.path)
        if minutes > 0 and minutes != lesson.duration_minutes:
            lesson.duration_minutes = minutes
            lesson.save(update_fields=['duration_minutes'])
    except Exception:
        pass


@login_required
def add_lesson(request, chapter_id):
    chapter = get_object_or_404(CourseChapter, id=chapter_id)
    course, redirect_resp = _require_course_teacher(request, chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.chapter = chapter
            lesson.save()
            _autoset_lesson_duration(lesson)

    return redirect('manage_content', course_id=course.id)


@login_required
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    course, redirect_resp = _require_course_teacher(request, lesson.chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            lesson = form.save()
            _autoset_lesson_duration(lesson)
            return redirect('manage_content', course_id=course.id)
    else:
        form = LessonForm(instance=lesson)

    return render(request, 'main/edit_lesson.html', {
        'form': form,
        'lesson': lesson,
        'course': course,
    })


@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    course, redirect_resp = _require_course_teacher(request, lesson.chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        lesson.delete()

    return redirect('manage_content', course_id=course.id)


# =========================
# A3 退款審核（老師 / 管理員）
# =========================

@login_required
def manage_refunds(request):
    if request.user.is_superuser:
        refunds = Refund.objects.select_related(
            'order', 'order__course', 'user'
        ).order_by('-created_at')
    else:
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return redirect('home')
        if profile.role != 'teacher':
            return redirect('home')
        refunds = Refund.objects.filter(
            order__course__teacher=request.user
        ).select_related('order', 'order__course', 'user').order_by('-created_at')

    return render(request, 'main/manage_refunds.html', {
        'refunds': refunds,
    })


@login_required
def process_refund(request, refund_id):
    refund = get_object_or_404(Refund, id=refund_id)

    # 權限：管理員或該課程講師
    is_teacher = (
        not request.user.is_superuser
        and refund.order.course
        and refund.order.course.teacher_id == request.user.id
    )
    if not (request.user.is_superuser or is_teacher):
        return redirect('home')

    if request.method == 'POST' and refund.status == 'pending':
        # 狀態轉換一律走 transitions —— 後台 admin 的批次動作呼叫的是同一份。
        action = request.POST.get('action')
        if action == 'approve':
            approve_refund(refund)
        elif action == 'reject':
            reject_refund(refund)

    return redirect('manage_refunds')


# =========================
# A6 通知中心
# =========================

@login_required
def notifications(request):
    notes = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'main/notifications.html', {
        'notifications': notes,
    })


@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
    return redirect('notifications')


# =========================
# A7 課程問答
# =========================

@login_required
def add_question(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    purchased = Enrollment.objects.filter(
        student=request.user, course=course
    ).exists()
    is_teacher = course.teacher_id == request.user.id

    if request.method == 'POST' and (purchased or is_teacher):
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.user = request.user
            q.course = course
            q.save()
            if not is_teacher:
                Notification.objects.create(
                    user=course.teacher,
                    title='課程有新提問',
                    content=f'課程「{course.title}」收到新的問題：{q.title}'
                )

    return redirect('course_detail', course_id=course.id)


@login_required
def add_answer(request, question_id):
    question = get_object_or_404(CourseQuestion, id=question_id)
    course = question.course

    is_teacher = course.teacher_id == request.user.id
    if not (is_teacher or request.user.is_superuser):
        return redirect('course_detail', course_id=course.id)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            a = form.save(commit=False)
            a.question = question
            a.user = request.user
            a.save()
            Notification.objects.create(
                user=question.user,
                title='你的提問已被回覆',
                content=f'課程「{course.title}」中你的問題「{question.title}」已有回答。'
            )

    return redirect('course_detail', course_id=course.id)


# =========================
# A8 課程審核（管理員）
# =========================

@login_required
def manage_audits(request):
    if not request.user.is_superuser:
        return redirect('home')

    audits = CourseAudit.objects.select_related(
        'course', 'course__teacher', 'reviewer'
    ).order_by('-created_at')

    return render(request, 'main/manage_audits.html', {
        'audits': audits,
    })


@login_required
def process_audit(request, audit_id):
    if not request.user.is_superuser:
        return redirect('home')

    audit = get_object_or_404(CourseAudit, id=audit_id)

    if request.method == 'POST':
        # 上架/退回一律走 transitions —— 後台的批次上架呼叫的是同一份，
        # 因此不存在繞過 CourseAudit 的旁路。
        action = request.POST.get('action')
        comment = request.POST.get('comment', '').strip()

        if action == 'approve':
            approve_course(audit.course, request.user, comment)
        elif action == 'reject':
            reject_course(audit.course, request.user, comment)

    return redirect('manage_audits')


# =========================
# A9 分潤收支與提領（講師 / 管理員）
#
# 分潤計算本身（RevenueRecord.recompute / create_for_order_item）是純計算，
# 已隨 fulfill_order／approve_refund 自動觸發，見 CONTEXT.md「分潤、收支與提領」。
# 這裡是講師查詢與提領申請的對外入口。
# =========================

def _require_teacher_profile(request):
    """回傳講師的 Profile；非講師或未設定角色一律回傳 None。"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return None
    return profile if profile.role == 'teacher' else None


@login_required
def my_revenue(request):
    """講師查詢收支分潤紀錄：每一筆的計算依據（比例、成本）與目前分潤規則。"""
    if not _require_teacher_profile(request):
        return redirect('home')

    records = RevenueRecord.objects.filter(
        teacher=request.user
    ).select_related('course', 'order').order_by('-created_at')

    paginator = Paginator(records, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    totals = records.filter(status='confirmed').aggregate(
        gross_amount=Sum('gross_amount'),
        marketing_cost=Sum('marketing_cost'),
        teacher_amount=Sum('teacher_amount'),
    )

    # 每門課目前適用的分潤規則（含未自訂過、套用預設值的課程）。
    course_rules = [
        CourseSplitSetting.for_course(course)
        for course in Course.objects.filter(teacher=request.user).order_by('title')
    ]

    return render(request, 'main/my_revenue.html', {
        'page_obj': page_obj,
        'totals': totals,
        'course_rules': course_rules,
        'available_balance': WithdrawalRequest.available_balance(request.user),
        'default_teacher_split': CourseSplitSetting.DEFAULT_TEACHER_SPLIT_PERCENT,
        'default_company_split': CourseSplitSetting.DEFAULT_COMPANY_SPLIT_PERCENT,
        'default_teacher_marketing_share': CourseSplitSetting.DEFAULT_TEACHER_MARKETING_SHARE_PERCENT,
        'default_company_marketing_share': CourseSplitSetting.DEFAULT_COMPANY_MARKETING_SHARE_PERCENT,
    })


@login_required
def my_withdrawals(request):
    """講師申請提領、查看自己的提領紀錄與目前可提領餘額。"""
    if not _require_teacher_profile(request):
        return redirect('home')

    error = None

    if request.method == 'POST':
        amount_raw = request.POST.get('amount', '').strip()
        try:
            amount = int(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            error = '請輸入正確的提領金額（正整數）。'
        else:
            withdrawal = WithdrawalRequest(teacher=request.user, amount=amount)
            try:
                withdrawal.save()
            except ValidationError as e:
                error = ' '.join(e.messages)
            else:
                Notification.objects.create(
                    user=request.user,
                    title='提領申請已送出',
                    content=f'你申請提領的 NT$ {amount} 已送出，等待處理。'
                )
                return redirect('my_withdrawals')

    withdrawals = WithdrawalRequest.objects.filter(
        teacher=request.user
    ).order_by('-requested_at')

    return render(request, 'main/my_withdrawals.html', {
        'withdrawals': withdrawals,
        'available_balance': WithdrawalRequest.available_balance(request.user),
        'error': error,
    })


@login_required
def manage_withdrawals(request):
    """後台查看：所有講師的提領申請，僅管理員可核准／拒絕。"""
    if not request.user.is_superuser:
        return redirect('home')

    withdrawals = WithdrawalRequest.objects.select_related(
        'teacher'
    ).order_by('-requested_at')

    return render(request, 'main/manage_withdrawals.html', {
        'withdrawals': withdrawals,
    })


@login_required
def process_withdrawal(request, withdrawal_id):
    if not request.user.is_superuser:
        return redirect('home')

    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)

    if request.method == 'POST':
        # 提領完成/拒絕一律走 transitions —— 與退款、審核同一套規則。
        action = request.POST.get('action')
        note = request.POST.get('note', '').strip()

        if action == 'complete':
            complete_withdrawal(withdrawal, note=note)
        elif action == 'reject':
            reject_withdrawal(withdrawal, note=note)

    return redirect('manage_withdrawals')


@login_required
def export_my_revenue_csv(request):
    """講師匯出自己的收支分潤紀錄。"""
    if not _require_teacher_profile(request):
        return redirect('home')

    response = create_csv_response('my_revenue.csv')
    writer = csv.writer(response)

    writer.writerow([
        'record_id',
        'course_id',
        'course_title',
        'order_id',
        'gross_amount',
        'marketing_cost',
        'teacher_split_percent',
        'company_split_percent',
        'teacher_marketing_share_percent',
        'company_marketing_share_percent',
        'teacher_amount',
        'company_amount',
        'status',
        'created_at',
        'reversed_at',
    ])

    records = RevenueRecord.objects.filter(
        teacher=request.user
    ).select_related('course', 'order').order_by('-created_at')

    for r in records:
        writer.writerow([
            r.id,
            r.course_id,
            r.course.title,
            r.order_id,
            r.gross_amount,
            r.marketing_cost,
            r.teacher_split_percent,
            r.company_split_percent,
            r.teacher_marketing_share_percent,
            r.company_marketing_share_percent,
            r.teacher_amount,
            r.company_amount,
            r.get_status_display(),
            r.created_at,
            r.reversed_at or '',
        ])

    return response


@login_required
def export_my_withdrawals_csv(request):
    """講師匯出自己的提領申請紀錄。"""
    if not _require_teacher_profile(request):
        return redirect('home')

    response = create_csv_response('my_withdrawals.csv')
    writer = csv.writer(response)

    writer.writerow([
        'withdrawal_id',
        'amount',
        'status',
        'note',
        'requested_at',
        'processed_at',
    ])

    withdrawals = WithdrawalRequest.objects.filter(
        teacher=request.user
    ).order_by('-requested_at')

    for w in withdrawals:
        writer.writerow([
            w.id,
            w.amount,
            w.get_status_display(),
            w.note or '',
            w.requested_at,
            w.processed_at or '',
        ])

    return response


# =========================
# Task 2 課程完成證書（PDF）
# =========================

def _course_completion(user, course):
    """回傳 (total_lessons, done_count, is_complete)。"""
    total = CourseLesson.objects.filter(chapter__course=course).count()
    done = LearningRecord.objects.filter(
        user=user, course=course
    ).exclude(lesson=None).values('lesson').distinct().count()
    is_complete = total > 0 and done >= total
    return total, done, is_complete


@login_required
def certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', course_id=course.id)

    total, done, is_complete = _course_completion(request.user, course)
    if not is_complete:
        return redirect('my_courses')

    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    # 繁體中文內建 CID 字型（免安裝字型檔）
    pdfmetrics.registerFont(UnicodeCIDFont('MSung-Light'))
    FONT = 'MSung-Light'

    buffer = io.BytesIO()
    W, H = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # 背景與外框
    c.setFillColorRGB(0.97, 0.97, 1.0)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColorRGB(0.31, 0.27, 0.90)
    c.setLineWidth(4)
    c.rect(15 * mm, 15 * mm, W - 30 * mm, H - 30 * mm, fill=0, stroke=1)
    c.setStrokeColorRGB(0.49, 0.36, 0.93)
    c.setLineWidth(1)
    c.rect(19 * mm, 19 * mm, W - 38 * mm, H - 38 * mm, fill=0, stroke=1)

    cx = W / 2

    c.setFillColorRGB(0.31, 0.27, 0.90)
    c.setFont(FONT, 40)
    c.drawCentredString(cx, H - 55 * mm, '結業證書')

    c.setFillColorRGB(0.42, 0.45, 0.5)
    c.setFont('Helvetica', 14)
    c.drawCentredString(cx, H - 66 * mm, 'CERTIFICATE OF COMPLETION')

    c.setFillColorRGB(0.2, 0.2, 0.25)
    c.setFont(FONT, 15)
    c.drawCentredString(cx, H - 90 * mm, '茲證明')

    c.setFillColorRGB(0.1, 0.1, 0.15)
    c.setFont(FONT, 30)
    c.drawCentredString(cx, H - 108 * mm, request.user.username)

    c.setStrokeColorRGB(0.7, 0.7, 0.75)
    c.setLineWidth(0.8)
    c.line(cx - 70 * mm, H - 112 * mm, cx + 70 * mm, H - 112 * mm)

    c.setFillColorRGB(0.2, 0.2, 0.25)
    c.setFont(FONT, 15)
    c.drawCentredString(cx, H - 126 * mm, '已完成本平台線上課程')

    c.setFillColorRGB(0.31, 0.27, 0.90)
    c.setFont(FONT, 22)
    c.drawCentredString(cx, H - 142 * mm, course.title)

    c.setFillColorRGB(0.3, 0.3, 0.35)
    c.setFont(FONT, 13)
    c.drawCentredString(cx, H - 158 * mm, f'授課講師：{course.teacher.username}　　完成日期：{timezone.now():%Y-%m-%d}')

    c.setFillColorRGB(0.55, 0.55, 0.6)
    c.setFont('Helvetica', 10)
    c.drawCentredString(cx, 26 * mm, f'Course Platform　|　證書編號 CERT-{course.id:04d}-{request.user.id:04d}')

    c.showPage()
    c.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'certificate_{course.id}_{request.user.id}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# =========================
# Task 4 講師公開頁
# =========================

def teacher_profile(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)

    # 評分統計用子查詢一次算完，不再逐課發查詢
    review_stats = Review.objects.filter(course=OuterRef('pk')).values('course')
    courses = list(
        Course.objects.filter(teacher=teacher, is_published=True)
        .select_related('category')
        .annotate(
            student_count=Count('enrollment', distinct=True),
            avg_rating_raw=Subquery(
                review_stats.annotate(a=Avg('rating')).values('a')[:1],
                output_field=FloatField()),
            review_count=Coalesce(
                Subquery(review_stats.annotate(n=Count('id')).values('n')[:1],
                         output_field=IntegerField()), 0),
        )
        .order_by('-created_at')
    )
    for c in courses:
        c.avg_rating = round(c.avg_rating_raw, 1) if c.avg_rating_raw else None

    total_students = Enrollment.objects.filter(
        course__teacher=teacher
    ).values('student').distinct().count()

    avg = Review.objects.filter(course__teacher=teacher).aggregate(a=Avg('rating'))['a']
    avg_rating = round(avg, 1) if avg else None
    review_count = Review.objects.filter(course__teacher=teacher).count()

    recent_reviews = Review.objects.filter(
        course__teacher=teacher
    ).select_related('user', 'course').order_by('-created_at')[:6]

    try:
        role_display = teacher.profile.get_role_display()
    except Profile.DoesNotExist:
        role_display = ''

    return render(request, 'main/teacher_profile.html', {
        'teacher': teacher,
        'role_display': role_display,
        'courses': courses,
        'course_count': len(courses),
        'total_students': total_students,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'recent_reviews': recent_reviews,
    })


# =========================
# 支援 Range 的媒體服務（開發環境播放影片用）
# =========================

def _file_iterator(path, start, length, chunk=8192):
    with open(path, 'rb') as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


def _range_file_response(request, full):
    """支援 HTTP Range 的檔案串流（影片才能拖曳進度條）。"""
    import os
    import re
    import mimetypes
    from django.http import StreamingHttpResponse

    ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
    size = os.path.getsize(full)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    m = re.match(r'bytes=(\d+)-(\d*)$', range_header)

    if m:
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            start = 0
        length = end - start + 1
        resp = StreamingHttpResponse(
            _file_iterator(full, start, length), status=206, content_type=ctype
        )
        resp['Content-Range'] = f'bytes {start}-{end}/{size}'
        resp['Content-Length'] = str(length)
    else:
        resp = StreamingHttpResponse(
            _file_iterator(full, 0, size), content_type=ctype
        )
        resp['Content-Length'] = str(size)

    resp['Accept-Ranges'] = 'bytes'
    return resp


@login_required
def stream_lesson_video(request, lesson_id):
    """付費影片的唯一出口。權限與 watch_lesson 相同。

    影片不再由 /media/ 直出 —— 那條路徑沒有任何存取檢查，等於只要知道
    網址就能把課程內容整包拿走。
    """
    lesson = get_object_or_404(
        CourseLesson.objects.select_related('chapter__course'), id=lesson_id
    )
    course = lesson.chapter.course

    enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    is_teacher = course.teacher_id == request.user.id
    if not (enrolled or is_teacher or lesson.is_free_preview):
        raise Http404('沒有這個影片')

    if not lesson.video_file:
        raise Http404('這個單元沒有上傳影片')

    return _range_file_response(request, lesson.video_file.path)


def serve_media(request, path):
    import os
    from django.conf import settings

    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    full = os.path.normpath(os.path.join(media_root, path))

    # 必須真的落在 MEDIA_ROOT 底下。startswith 會讓 <media_root>_evil/ 這種
    # 同層兄弟目錄通過，commonpath 不會。
    try:
        inside = os.path.commonpath([full, media_root]) == media_root
    except ValueError:          # 不同磁碟機
        inside = False
    if not inside or not os.path.isfile(full):
        raise Http404('media not found')

    # 課程影片一律改走 stream_lesson_video（會檢查購課），不從這裡直出。
    rel = os.path.relpath(full, media_root).replace('\\', '/')
    if rel.startswith('course_videos/'):
        raise Http404('media not found')

    return _range_file_response(request, full)



# ===== 快速登入（OAuth）／合購購物車／課程公告留言／教師問答 =====
# 上游分支沒有這幾個功能，從本機分支搬過來，邏輯與變數名稱不變。

def _attach_reviews(courses):
    """一次查完所有課程的評分統計，避免每堂課各發一次查詢（遠端 DB 的 N+1 效能殺手）。
    courses 若為 QuerySet，呼叫後其 _result_cache 會被填入已標記 avg_rating/review_count
    的物件，後續重新迭代該 QuerySet（例如樣板的 {% for %}）會直接用到快取，不需接收回傳值。"""
    courses = list(courses)
    ids = [c.id for c in courses]
    stats_map = {
        row['course']: row
        for row in Review.objects.filter(course_id__in=ids)
        .values('course')
        .annotate(avg=Avg('rating'), n=Count('id'))
    }
    for c in courses:
        s = stats_map.get(c.id)
        c.avg_rating = round(s['avg'], 1) if s and s['avg'] else None
        c.review_count = s['n'] if s else 0
    return courses


def _finalize_paid_order(order):
    """付款成功後：開通課程、標記優惠券、發通知（具冪等性）。"""
    if order.status == 'paid':
        return
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


def _group_cart_items_by_bundle(items):
    """把購物車項目依合購組合分組，回傳 (display_bundles, loose_items)。
    display_bundles 每筆含 bundle/items/is_intact/individual_total。"""
    bundle_groups = {}
    loose_items = []
    for item in items:
        if item.bundle_id:
            bundle_groups.setdefault(item.bundle_id, []).append(item)
        else:
            loose_items.append(item)

    display_bundles = []
    for group_items in bundle_groups.values():
        bundle = group_items[0].bundle
        bundle_course_ids = set(bundle.courses.values_list('id', flat=True))
        group_course_ids = {gi.course_id for gi in group_items}
        is_intact = bundle_course_ids == group_course_ids and bundle.is_active
        display_bundles.append({
            'bundle': bundle,
            'items': group_items,
            'is_intact': is_intact,
            'individual_total': sum(gi.course.get_effective_price() for gi in group_items),
        })

    return display_bundles, loose_items


def _is_teacher(profile):
    """單一帳號體系：role=='teacher'（傳統教師帳號）或 is_teacher（Admin 額外授權）皆可使用教師專區。"""
    return profile.role == 'teacher' or profile.is_teacher


def _login_error_redirect(message):
    return redirect(f"{reverse('login')}?{urlencode({'error': message})}")


def _post_login_redirect(user):
    # 不論學生或具備教師權限的使用者，登入後一律回到主頁；教師專區只能透過
    # 導覽列的「進入教師專區」按鈕主動進入，絕不在登入當下直接跳轉過去。
    if user.is_superuser:
        return redirect('/admin/')
    return redirect('home')


def add_announcement(request, course_id):
    course, redirect_resp = _require_course_teacher(request, course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.course = course
            announcement.author = request.user
            announcement.save()

    return redirect('manage_content', course_id=course.id)


def add_bundle_to_cart(request, bundle_id):
    bundle = get_object_or_404(CourseBundle, id=bundle_id, is_active=True)
    courses = list(bundle.courses.all())

    already_owns = Enrollment.objects.filter(
        student=request.user, course__in=courses
    ).exists()
    if already_owns:
        return redirect('course_detail', course_id=courses[0].id if courses else 0)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    for course in courses:
        CartItem.objects.update_or_create(
            cart=cart, course=course, defaults={'bundle': bundle}
        )

    return redirect('view_cart')


def add_comment(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.course = course
            comment.save()

    return redirect('course_detail', course_id=course.id)


def course_catalog(request):
    """完整課程總覽：搜尋、分類篩選、排序、分頁——從首頁搬過來，邏輯與變數名稱不變。"""
    sort = request.GET.get('sort', 'newest')
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()

    qs = Course.objects.filter(is_published=True).select_related('teacher', 'category')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(teacher__username__icontains=q))
    if cat:
        qs = qs.filter(category__name=cat)

    qs = qs.annotate(student_count=Count('enrollment', distinct=True))

    sort_map = {
        'newest': '-created_at',
        'popular': '-student_count',
        'price_asc': 'price',
        'price_desc': '-price',
    }
    if sort not in sort_map:
        sort = 'newest'
    if sort == 'popular':
        qs = qs.order_by('-student_count', '-created_at')
    else:
        qs = qs.order_by(sort_map[sort])

    paginator = Paginator(qs, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    _attach_reviews(page_obj.object_list)

    categories = CourseCategory.objects.order_by('name')

    return render(request, 'main/course_catalog.html', {
        'page_obj': page_obj,
        'sort': sort,
        'q': q,
        'cat': cat,
        'categories': categories,
        'sort_options': [
            ('newest', '最新'),
            ('popular', '熱門'),
            ('price_asc', '價格低→高'),
            ('price_desc', '價格高→低'),
        ],
    })


def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(CourseAnnouncement, id=announcement_id)
    course, redirect_resp = _require_course_teacher(request, announcement.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        announcement.delete()

    return redirect('manage_content', course_id=course.id)


def google_login(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return _login_error_redirect('Google 登入尚未設定。')
    state = oauth.new_state()
    request.session['google_oauth_state'] = state
    return redirect(oauth.build_google_auth_url(request, state))


def google_oauth_callback(request):
    error = request.GET.get('error')
    if error:
        return _login_error_redirect('Google 登入已取消。')

    state = request.GET.get('state')
    expected_state = request.session.pop('google_oauth_state', None)
    if not state or not expected_state or state != expected_state:
        return _login_error_redirect('登入驗證失敗，請再試一次。')

    code = request.GET.get('code')
    if not code:
        return _login_error_redirect('Google 未提供授權碼。')

    try:
        provider_id, email, name = oauth.fetch_google_profile(request, code)
        user = oauth.get_or_create_user('google', provider_id, email, name)
    except oauth.OAuthError:
        return _login_error_redirect('Google 登入失敗，請稍後再試。')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return _post_login_redirect(user)


def line_login(request):
    if not settings.LINE_LOGIN_CHANNEL_ID:
        return _login_error_redirect('LINE 登入尚未設定。')
    state = oauth.new_state()
    request.session['line_oauth_state'] = state
    return redirect(oauth.build_line_auth_url(request, state))


def line_oauth_callback(request):
    error = request.GET.get('error')
    if error:
        return _login_error_redirect('LINE 登入已取消。')

    state = request.GET.get('state')
    expected_state = request.session.pop('line_oauth_state', None)
    if not state or not expected_state or state != expected_state:
        return _login_error_redirect('登入驗證失敗，請再試一次。')

    code = request.GET.get('code')
    if not code:
        return _login_error_redirect('LINE 未提供授權碼。')

    try:
        provider_id, email, name = oauth.fetch_line_profile(request, code)
        user = oauth.get_or_create_user('line', provider_id, email, name)
    except oauth.OAuthError:
        return _login_error_redirect('LINE 登入失敗，請稍後再試。')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return _post_login_redirect(user)


def teacher_qna(request):
    try:
        profile = request.user.profile
        if not _is_teacher(profile):
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    questions = CourseQuestion.objects.filter(
        course__teacher=request.user
    ).select_related('user', 'course').prefetch_related('answers').annotate(
        answer_count=Count('answers')
    ).order_by('answer_count', '-created_at')

    return render(request, 'main/teacher_qna.html', {
        'questions': questions,
        'answer_form': AnswerForm(),
    })
