import csv
import json
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Q
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.http import urlencode

from django.utils import timezone

from .models import (
    Course,
    CourseLesson,
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
    Promotion,
    CourseCategory,
    TeacherBankAccount,
    WithdrawalRequest,
    CourseBundle,
    CourseAnnouncement,
    CourseComment,
)

from .forms import (
    RegisterForm,
    CouponApplyForm,
    ReviewForm,
    ChapterForm,
    LessonForm,
    QuestionForm,
    AnswerForm,
    ProfileEditForm,
    TeacherBankAccountForm,
    WithdrawalRequestForm,
    AnnouncementForm,
    CommentForm,
)

MIN_WITHDRAWAL_AMOUNT = 500


def _is_teacher(profile):
    """單一帳號體系：role=='teacher'（傳統教師帳號）或 is_teacher（Admin 額外授權）皆可使用教師專區。"""
    return profile.role == 'teacher' or profile.is_teacher

from .payments import gateway
from . import oauth


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


def home(request):
    """編輯策展式首頁：精選/熱門/最新/主題故事區塊 + 品牌信任數字，完整篩選/排序/分頁另見 course_catalog。"""
    categories = CourseCategory.objects.order_by('name')
    total_students = Enrollment.objects.values('student').distinct().count()
    total_courses = Course.objects.filter(is_published=True).count()
    total_enrollments = Enrollment.objects.count()
    total_teachers = User.objects.filter(profile__is_teacher=True).count()
    avg_all = Review.objects.aggregate(a=Avg('rating'))['a']
    avg_all = round(avg_all, 1) if avg_all else 4.8

    base_pub = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    popular_courses = _attach_reviews(
        base_pub.annotate(sc=Count('enrollment', distinct=True)).order_by('-sc', '-created_at')[:10]
    )
    latest_courses = _attach_reviews(base_pub.order_by('-created_at')[:10])

    now = timezone.now()
    funding_courses = list(
        base_pub.filter(
            is_crowdfunding=True,
            funding_start_date__lte=now,
            funding_end_date__gte=now,
        ).order_by('funding_end_date')[:10]
    )

    # 主題故事區塊：依課程分類分組，取代原本電商式的排序/篩選型錄頁
    theme_sections = []
    for category in categories:
        cat_courses = _attach_reviews(base_pub.filter(category=category).order_by('-created_at')[:8])
        if cat_courses:
            theme_sections.append({'category': category, 'courses': cat_courses})

    return render(request, 'main/home.html', {
        'categories': categories,
        'total_students': total_students,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_teachers': total_teachers,
        'avg_all': avg_all,
        'popular_courses': popular_courses,
        'latest_courses': latest_courses,
        'funding_courses': funding_courses,
        'theme_sections': theme_sections,
    })


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


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

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

    try:
        teacher_bio = course.teacher.profile.bio
    except Profile.DoesNotExist:
        teacher_bio = None

    # 課程統計（銷售頁用）
    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    total_minutes = CourseLesson.objects.filter(chapter__course=course).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    student_count = Enrollment.objects.filter(course=course).count()

    # 合購優惠：本課程參與的啟用中組合
    bundles = course.bundles.filter(is_active=True).prefetch_related('courses')
    if request.user.is_authenticated:
        for bundle in bundles:
            bundle.user_owns_any = Enrollment.objects.filter(
                student=request.user, course__in=bundle.courses.all()
            ).exists()
    else:
        for bundle in bundles:
            bundle.user_owns_any = False

    # 課程公告：僅已購買學員／該課程教師／Admin 可見
    can_see_announcements = already_purchased or is_course_teacher or request.user.is_superuser
    announcements = course.announcements.select_related('author').all() if can_see_announcements else []

    # 課程留言：任何登入使用者皆可留言，與需購買才能發問的問答區區隔
    comments = course.comments.select_related('user').all()

    # 試看影片：彙整本課程所有標記免費試看的單元
    preview_lessons = CourseLesson.objects.filter(
        chapter__course=course, is_free_preview=True
    ).select_related('chapter').order_by('chapter__sort_order', 'sort_order')

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
        'teacher_bio': teacher_bio,
        'total_lessons': total_lessons,
        'total_minutes': total_minutes,
        'student_count': student_count,
        'bundles': bundles,
        'can_see_announcements': can_see_announcements,
        'announcements': announcements,
        'comments': comments,
        'comment_form': CommentForm(),
        'preview_lessons': preview_lessons,
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

            # 所有新註冊帳號一律為學生身分；教師權限只能由 Admin 後台另外授予。
            Profile.objects.create(user=user, role='student')

            return redirect('register_success')
    else:
        form = RegisterForm()

    return render(request, 'main/register.html', {
        'form': form,
    })


def register_success(request):
    return render(request, 'main/register_success.html')


def _post_login_redirect(user):
    # 不論學生或具備教師權限的使用者，登入後一律回到主頁；教師專區只能透過
    # 導覽列的「進入教師專區」按鈕主動進入，絕不在登入當下直接跳轉過去。
    if user.is_superuser:
        return redirect('/admin/')
    return redirect('home')


def login_view(request):
    error_message = request.GET.get('error') or None

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
            return _post_login_redirect(user)
        else:
            error_message = '帳號 / Email 或密碼錯誤。'

    return render(request, 'main/login.html', {
        'error_message': error_message,
    })


def logout_view(request):
    logout(request)
    return redirect('home')


def _login_error_redirect(message):
    return redirect(f"{reverse('login')}?{urlencode({'error': message})}")


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
    # 每個帳號本質上都具備學生身份（教師權限只是額外附加），此頁不限角色。
    try:
        request.user.profile
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


def _teacher_finance_summary(user):
    """依各課程的分潤比例，計算教師目前的預估淨收入與可提領餘額。"""
    courses = Course.objects.filter(teacher=user)
    course_net = {}
    total_gross = 0
    total_net = 0

    for course in courses:
        # 用 OrderItem 聚合（而非 Order.course），才能涵蓋購物車/合購優惠等多課程訂單
        # （這類訂單 Order.course 為 None，比照 platform_analytics 的熱銷課程統計做法）
        gross = OrderItem.objects.filter(
            course=course, order__status='paid'
        ).aggregate(total=Sum('price'))['total'] or 0
        net = gross * course.teacher_revenue_share // 100
        course_net[course.id] = {'gross_revenue': gross, 'net_revenue': net}
        total_gross += gross
        total_net += net

    already_withdrawn = WithdrawalRequest.objects.filter(
        teacher=user, status='APPROVED'
    ).aggregate(s=Sum('amount'))['s'] or 0
    pending_withdrawal = WithdrawalRequest.objects.filter(
        teacher=user, status='PENDING'
    ).aggregate(s=Sum('amount'))['s'] or 0

    available_balance = max(0, total_net - already_withdrawn - pending_withdrawal)

    return {
        'course_net': course_net,
        'total_gross_revenue': total_gross,
        'total_net_income': total_net,
        'total_withdrawn': already_withdrawn,
        'pending_withdrawal_amount': pending_withdrawal,
        'available_balance': available_balance,
    }


@login_required
def teacher_dashboard(request):
    """單頁式財務與提領儀表板：淨收入、提領申請、提領明細，不含任何課程資訊。"""
    try:
        profile = request.user.profile

        if not _is_teacher(profile):
            return redirect('home')

    except Profile.DoesNotExist:
        return redirect('home')

    bank_account = TeacherBankAccount.objects.filter(teacher=request.user).first()
    finance = _teacher_finance_summary(request.user)

    form = None
    if request.method == 'POST':
        if bank_account:
            form = WithdrawalRequestForm(
                request.POST,
                available_balance=finance['available_balance'],
                min_amount=MIN_WITHDRAWAL_AMOUNT,
            )
            if form.is_valid():
                snapshot = (
                    f"{bank_account.bank_name}"
                    f"{' ' + bank_account.branch_name if bank_account.branch_name else ''} - "
                    f"{bank_account.account_name} {bank_account.account_number}"
                )
                WithdrawalRequest.objects.create(
                    teacher=request.user,
                    amount=form.cleaned_data['amount'],
                    bank_info_snapshot=snapshot,
                    status='PENDING',
                )
                return redirect('teacher_dashboard')

    if form is None:
        form = WithdrawalRequestForm(
            available_balance=finance['available_balance'],
            min_amount=MIN_WITHDRAWAL_AMOUNT,
        )

    unanswered_questions = CourseQuestion.objects.filter(
        course__teacher=request.user
    ).exclude(answers__isnull=False).count()

    withdrawals = WithdrawalRequest.objects.filter(
        teacher=request.user
    ).order_by('-created_at')

    return render(request, 'main/teacher_dashboard.html', {
        'finance': finance,
        'min_withdrawal_amount': MIN_WITHDRAWAL_AMOUNT,
        'bank_account': bank_account,
        'form': form,
        'withdrawals': withdrawals,
        'unanswered_questions': unanswered_questions,
    })


@login_required
def my_courses(request):
    try:
        request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related('course', 'course__teacher', 'course__category')

    for enrollment in enrollments:
        enrollment.watch_minutes = LearningRecord.objects.filter(
            user=request.user,
            course=enrollment.course
        ).aggregate(
            total=Sum('minutes')
        )['total'] or 0

        course_total = CourseLesson.objects.filter(
            chapter__course=enrollment.course
        ).aggregate(total=Sum('duration_minutes'))['total'] or 0
        enrollment.course_total_minutes = course_total

        if course_total > 0:
            pct = int(min(enrollment.watch_minutes, course_total) / course_total * 100)
        else:
            pct = 0
        enrollment.progress = pct

        # 退款整合進我的課程：找該課的已付款訂單與退款狀態
        order = Order.objects.filter(
            user=request.user, course=enrollment.course, status='paid'
        ).order_by('-id').first()
        enrollment.order = order
        enrollment.refund = None
        if order:
            enrollment.refund = Refund.objects.filter(order=order).order_by('-id').first()

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
    course = get_object_or_404(Course, id=course_id)

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

    list_price = course.price
    original_price = course.get_effective_price()
    coupon = None
    discount_amount = 0
    final_price = original_price
    error_message = None
    success_message = None
    selected_code = ''

    if request.method == 'POST':
        # action：apply=只套用預覽折扣、buy=確認購買
        action = request.POST.get('action', 'buy')
        coupon_code = request.POST.get('coupon_code', '').strip()
        selected_code = coupon_code

        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code)

            except Coupon.DoesNotExist:
                coupon = None
                error_message = '找不到這張優惠券。'

            if coupon:
                if not coupon.is_valid_now():
                    error_message = '這張優惠券目前不可使用。'
                    coupon = None

                else:
                    discount_amount = coupon.calculate_discount(original_price)

                    if discount_amount <= 0:
                        error_message = '此優惠券未達最低消費金額或無法套用。'
                        coupon = None
                        discount_amount = 0

                    else:
                        final_price = original_price - discount_amount
                        success_message = f'優惠券已套用，折抵 NT$ {discount_amount}。'
        elif action == 'buy':
            success_message = None  # 沒輸入券，直接原價購買

        # 只有按「確認購買」且沒有錯誤時才成立「待付款」訂單，導向付款頁；
        # 按「套用優惠券」只重新整理頁面顯示折扣預覽。付款完成後才會開通課程。
        if action == 'buy' and not error_message:
            order = Order.objects.create(
                user=request.user,
                course=course,
                coupon=coupon,
                original_price=original_price,
                discount_amount=discount_amount,
                final_price=final_price,
                status='pending'
            )
            OrderItem.objects.create(
                order=order, course=course, price=original_price,
                discount_amount=discount_amount, paid_amount=final_price,
            )
            Payment.objects.create(
                order=order, amount=final_price, status='pending', method='mock'
            )
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
        'list_price': list_price,
        'original_price': original_price,
        'discount_amount': discount_amount,
        'final_price': final_price,
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
def student_analytics(request):
    try:
        request.user.profile
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
        if not _is_teacher(profile):
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    teacher_courses = Course.objects.filter(
        teacher=request.user
    )

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
        purchase_count = Enrollment.objects.filter(course=course).count()

        revenue = Order.objects.filter(
            course=course,
            status='paid'
        ).aggregate(
            total=Sum('final_price')
        )['total'] or 0

        watch_minutes = LearningRecord.objects.filter(
            course=course
        ).aggregate(
            total=Sum('minutes')
        )['total'] or 0

        avg_rating = Review.objects.filter(
            course=course
        ).aggregate(
            avg=Avg('rating')
        )['avg'] or 0

        course_labels.append(course.title)
        purchase_counts.append(purchase_count)
        revenue_data.append(revenue)
        watch_minutes_data.append(watch_minutes)
        rating_data.append(round(avg_rating, 1))

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
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
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
    course = get_object_or_404(Course, id=course_id)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_detail', course_id=course.id)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    CartItem.objects.get_or_create(cart=cart, course=course)

    return redirect('view_cart')


@login_required
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


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = list(cart.items.select_related('course', 'course__teacher', 'bundle').all())
    total = sum(item.course.get_effective_price() for item in items)

    display_bundles, loose_items = _group_cart_items_by_bundle(items)

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
        'display_bundles': display_bundles,
        'loose_items': loose_items,
        'total': total,
        'available_coupons': available_coupons,
        'claimed_ids': claimed_ids,
        'my_coupons': my_coupons,
    })


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect('view_cart')


@login_required
def cart_checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = list(cart.items.select_related('course', 'bundle').all())
    now = timezone.now()

    # A5：有效促銷 → course_id 對應 Promotion
    promo_map = {}
    active_promos = Promotion.objects.filter(
        is_active=True, start_date__lte=now, end_date__gte=now
    ).prefetch_related('courses')
    for promo in active_promos:
        for c in promo.courses.all():
            promo_map.setdefault(c.id, promo)

    # A5：整車套用一張優惠券（依購物車總額計算，逐筆分攤）
    coupon = None
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip()
        if code:
            coupon = Coupon.objects.filter(code__iexact=code).first()
            if coupon and not coupon.is_valid_now():
                coupon = None

    # 只結帳尚未購買的課程
    items = [i for i in items if not Enrollment.objects.filter(
        student=request.user, course=i.course).exists()]
    if not items:
        return redirect('view_cart')

    cart_total = sum(i.course.get_effective_price() for i in items)
    coupon_discount = coupon.calculate_discount(cart_total) if coupon else 0

    # 合購優惠：組合完整才套用合購價（依各課程原價比例分攤，餘數分給組內最後一筆對齊總額），
    # 組合被拆散（使用者移除其中一堂或已購買其中一堂）就退回個別計價並清空 bundle 標記
    bundle_groups = {}
    loose_items = []
    for item in items:
        if item.bundle_id:
            bundle_groups.setdefault(item.bundle_id, []).append(item)
        else:
            loose_items.append(item)

    item_price = {}
    total_original = 0
    total_discount = 0

    for group_items in bundle_groups.values():
        bundle = group_items[0].bundle
        bundle_course_ids = set(bundle.courses.values_list('id', flat=True))
        group_course_ids = {gi.course_id for gi in group_items}

        if not bundle.is_active or bundle_course_ids != group_course_ids:
            for gi in group_items:
                gi.bundle = None
                gi.save(update_fields=['bundle'])
            loose_items.extend(group_items)
            continue

        individual_prices = {gi.id: gi.course.get_effective_price() for gi in group_items}
        group_total_individual = sum(individual_prices.values())
        allocated = 0
        for idx, gi in enumerate(group_items):
            if idx == len(group_items) - 1:
                price = bundle.bundle_price - allocated
            else:
                price = individual_prices[gi.id] * bundle.bundle_price // group_total_individual
                allocated += price
            item_price[gi.id] = price
        total_original += group_total_individual
        total_discount += (group_total_individual - bundle.bundle_price)

    for item in loose_items:
        original = item.course.get_effective_price()
        promo = promo_map.get(item.course.id)
        promo_disc = 0
        if promo:
            if promo.discount_type == 'amount':
                promo_disc = min(promo.discount_value, original)
            else:
                promo_disc = int(original * promo.discount_value / 100)
        item_price[item.id] = original - promo_disc
        total_original += original
        total_discount += promo_disc

    total_discount += coupon_discount
    final_price = max(total_original - total_discount, 0)

    # 優惠券折扣依各項目「合購/促銷折扣後」的價格比例分攤，得出每個項目的實付金額
    item_discount = {}
    item_paid = {}
    price_sum = sum(item_price.values()) or 1
    allocated_coupon = 0
    for idx, item in enumerate(items):
        if idx == len(items) - 1:
            coupon_share = coupon_discount - allocated_coupon
        else:
            coupon_share = item_price[item.id] * coupon_discount // price_sum
            allocated_coupon += coupon_share
        item_discount[item.id] = coupon_share
        item_paid[item.id] = item_price[item.id] - coupon_share

    # 建立單一「待付款」訂單（多課程訂單，course=None），付款完成後才開通
    order = Order.objects.create(
        user=request.user,
        course=None,
        coupon=coupon if coupon_discount > 0 else None,
        original_price=total_original,
        discount_amount=total_discount,
        final_price=final_price,
        status='pending'
    )
    for item in items:
        OrderItem.objects.create(
            order=order, course=item.course, price=item_price[item.id],
            discount_amount=item_discount[item.id], paid_amount=item_paid[item.id],
        )
    Payment.objects.create(
        order=order, amount=final_price, status='pending', method='mock'
    )

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


@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'paid':
        return redirect('order_success', order_id=order.id)

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
                _finalize_paid_order(order)
                return redirect('order_success', order_id=order.id)
            error = result.message
            method = 'credit_card'

        elif action == 'confirm_offline':
            # 使用者回報已完成 ATM 轉帳 / 超商繳費（模擬銀行/超商回拋）
            result = gateway.confirm_offline(payment_obj)
            if result.success:
                _mark_payment_paid(payment_obj, result)
                _finalize_paid_order(order)
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
    course = get_object_or_404(Course, id=course_id)
    favorite = Favorite.objects.filter(user=request.user, course=course).first()

    if favorite:
        favorite.delete()
    else:
        Favorite.objects.create(user=request.user, course=course)

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
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

    if not _is_teacher(profile):
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
        'announcements': course.announcements.all(),
        'announcement_form': AnnouncementForm(),
    })


@login_required
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


@login_required
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(CourseAnnouncement, id=announcement_id)
    course, redirect_resp = _require_course_teacher(request, announcement.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        announcement.delete()

    return redirect('manage_content', course_id=course.id)


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
        if not _is_teacher(profile):
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

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and refund.status == 'pending':
            refund.status = 'approved'
            refund.processed_at = timezone.now()
            refund.save()
            order = refund.order
            order.status = 'refunded'
            order.save()
            Notification.objects.create(
                user=refund.user,
                title='退款已通過',
                content=f'訂單 #{order.id} 的退款申請已通過，將退還 NT$ {refund.amount}。'
            )
        elif action == 'reject' and refund.status == 'pending':
            refund.status = 'rejected'
            refund.processed_at = timezone.now()
            refund.save()
            Notification.objects.create(
                user=refund.user,
                title='退款未通過',
                content=f'訂單 #{refund.order.id} 的退款申請未通過。'
            )

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

    is_course_teacher = course.teacher_id == request.user.id
    if not (is_course_teacher or request.user.is_superuser):
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

    if request.POST.get('source') == 'teacher_qna':
        return redirect('teacher_qna')
    return redirect('course_detail', course_id=course.id)


# =========================
# 課程留言區（開放任何登入使用者，與需購買才能發問的問答區區隔）
# =========================

@login_required
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


# =========================
# 教師專區：Q&A 管理
# =========================

@login_required
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


# =========================
# 教師專區：銀行帳戶與提領
# =========================

@login_required
def edit_bank_account(request):
    try:
        profile = request.user.profile
        if not _is_teacher(profile):
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    bank_account, _created = TeacherBankAccount.objects.get_or_create(
        teacher=request.user,
        defaults={'bank_name': '', 'account_name': '', 'account_number': ''}
    )

    if request.method == 'POST':
        form = TeacherBankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            form.save()
            return redirect('teacher_dashboard')
    else:
        form = TeacherBankAccountForm(instance=bank_account)

    return render(request, 'main/edit_bank_account.html', {
        'form': form,
    })


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
        action = request.POST.get('action')
        comment = request.POST.get('comment', '').strip()

        if action == 'approve':
            audit.status = 'approved'
            audit.reviewer = request.user
            audit.comment = comment
            audit.reviewed_at = timezone.now()
            audit.save()
            course = audit.course
            course.is_published = True
            course.save()
            Notification.objects.create(
                user=course.teacher,
                title='課程審核通過',
                content=f'你的課程「{course.title}」已通過審核並上架。'
            )
        elif action == 'reject':
            audit.status = 'rejected'
            audit.reviewer = request.user
            audit.comment = comment
            audit.reviewed_at = timezone.now()
            audit.save()
            course = audit.course
            course.is_published = False
            course.save()
            Notification.objects.create(
                user=course.teacher,
                title='課程審核未通過',
                content=f'你的課程「{course.title}」未通過審核。原因：{comment or "未提供"}'
            )

    return redirect('manage_audits')

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

    courses = list(
        Course.objects.filter(teacher=teacher, is_published=True)
        .select_related('category')
        .annotate(student_count=Count('enrollment', distinct=True))
        .order_by('-created_at')
    )
    for c in courses:
        stats = Review.objects.filter(course=c).aggregate(avg=Avg('rating'), n=Count('id'))
        c.avg_rating = round(stats['avg'], 1) if stats['avg'] else None
        c.review_count = stats['n']

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


def serve_media(request, path):
    import os
    import re
    import mimetypes
    from django.conf import settings
    from django.http import StreamingHttpResponse, Http404

    media_root = str(settings.MEDIA_ROOT)
    full = os.path.normpath(os.path.join(media_root, path))
    if not full.startswith(media_root) or not os.path.isfile(full):
        raise Http404('media not found')

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
