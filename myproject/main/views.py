import csv
import json
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .decorators import require_teacher, require_student, require_superuser
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
)
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme, urlencode

from django.utils import timezone

from .models import (
    Course,
    CourseLesson,
    LessonMaterial,
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
    TeacherFollow,
    TeacherColumn,
    TeacherArticle,
    TeacherMaterial,
    ColumnSubscription,
    TeacherBankAccount,
    MarketingRequest,
    MarketingPlan,
    VMAccessRequest,
    CourseCertificate,
)

from .certificates import render_certificate_pdf

from .forms import (
    RegisterForm,
    CourseForm,
    CouponApplyForm,
    ReviewForm,
    ChapterForm,
    LessonForm,
    LessonMaterialForm,
    QuestionForm,
    AnswerForm,
    ProfileEditForm,
    AnnouncementForm,
    CommentForm,
    ColumnForm,
    ArticleForm,
    MaterialForm,
    TeacherBankAccountForm,
    MarketingRequestForm,
    VMAccessRequestForm,
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

    _attach_reviews(page_obj.object_list)

    categories = list(CourseCategory.objects.order_by('name'))
    _CATEGORY_ICONS = {
        '個人成長': 'fa-seedling', '商業管理': 'fa-briefcase', '學術教育': 'fa-graduation-cap',
        '影視製作': 'fa-film', '手作生活': 'fa-palette', '攝影剪輯': 'fa-camera',
        '程式設計': 'fa-code', '程式': 'fa-code', '設計': 'fa-pen-nib', '語言': 'fa-language',
        '音樂': 'fa-music', '行銷': 'fa-bullhorn', '理財': 'fa-coins', '健身': 'fa-dumbbell',
        '料理': 'fa-utensils', '攝影': 'fa-camera', '數據': 'fa-chart-line',
    }
    for c in categories:
        icon = 'fa-folder-open'
        for key, val in _CATEGORY_ICONS.items():
            if key in c.name:
                icon = val
                break
        c.icon = icon
    total_students = Enrollment.objects.values('student').distinct().count()
    total_courses = Course.objects.filter(is_published=True).count()
    total_teachers = Course.objects.filter(is_published=True).values('teacher').distinct().count()
    total_learning_hours = (LearningRecord.objects.aggregate(t=Sum('minutes'))['t'] or 0) // 60
    avg_all = Review.objects.aggregate(a=Avg('rating'))['a']
    avg_all = round(avg_all, 1) if avg_all else 4.8

    def _decorate(qs):
        return _attach_reviews(qs)

    base_pub = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    popular_courses = _decorate(
        base_pub.annotate(sc=Count('enrollment', distinct=True)).order_by('-sc', '-created_at')[:10]
    )
    latest_courses = _decorate(base_pub.order_by('-created_at')[:10])
    hero_courses = _decorate(base_pub.order_by('?')[:6])

    now = timezone.now()
    funding_courses = list(
        base_pub.filter(
            is_crowdfunding=True,
            funding_start_date__lte=now,
            funding_end_date__gte=now,
        ).order_by('funding_end_date')[:10]
    )

    showcase_columns = []
    showcase_image_urls = [c.image.url for c in base_pub.exclude(image='') if c.image]
    if showcase_image_urls:
        SHOWCASE_COLUMNS = 5
        SHOWCASE_IMAGES_PER_COLUMN = 8
        n = len(showcase_image_urls)
        showcase_columns = [
            [showcase_image_urls[(col * 3 + i) % n] for i in range(SHOWCASE_IMAGES_PER_COLUMN)]
            for col in range(SHOWCASE_COLUMNS)
        ]

    from . import ai_assistant

    continue_learning = []
    if request.user.is_authenticated:
        enrolled_courses = Course.objects.filter(
            enrollment__student=request.user, is_published=True,
        ).select_related('teacher', 'teacher__profile', 'category')
        for ec in enrolled_courses[:6]:
            ec_total = CourseLesson.objects.filter(chapter__course=ec).count()
            if ec_total == 0:
                continue
            ec_done = LessonProgress.objects.filter(
                user=request.user, lesson__chapter__course=ec, is_completed=True,
            ).count()
            ec_pct = round(ec_done / ec_total * 100) if ec_total else 0
            if ec_pct < 100:
                completed_ids = set(
                    LessonProgress.objects.filter(
                        user=request.user, lesson__chapter__course=ec, is_completed=True,
                    ).values_list('lesson_id', flat=True)
                )
                next_lesson = CourseLesson.objects.filter(
                    chapter__course=ec,
                ).exclude(id__in=completed_ids).order_by('chapter__sort_order', 'sort_order').first()
                continue_learning.append({
                    'course': ec,
                    'progress': ec_pct,
                    'done': ec_done,
                    'total': ec_total,
                    'next_lesson': next_lesson,
                })

    theme_sections = []
    for category in CourseCategory.objects.order_by('name'):
        cat_courses = list(
            base_pub.filter(category=category)
            .annotate(_pop=Count('enrollment', distinct=True))
            .order_by('-_pop')[:4]
        )
        if cat_courses:
            _attach_reviews(cat_courses)
            theme_sections.append({'category': category, 'courses': cat_courses})

    return render(request, 'main/home.html', {
        'page_obj': page_obj,
        'sort': sort,
        'q': q,
        'cat': cat,
        'categories': categories,
        'platform_faqs': ai_assistant.PLATFORM_FAQS,
        'total_students': total_students,
        'total_courses': total_courses,
        'total_teachers': total_teachers,
        'avg_all': avg_all,
        'popular_courses': popular_courses,
        'latest_courses': latest_courses,
        'hero_courses': hero_courses,
        'funding_courses': funding_courses,
        'showcase_columns': showcase_columns,
        'theme_sections': theme_sections,
        'continue_learning': continue_learning,
        'sort_options': [
            ('newest', '最新'),
            ('popular', '熱門'),
            ('price_asc', '價格低→高'),
            ('price_desc', '價格高→低'),
        ],
    })

def _course_stats_annotations():
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

    rating_distribution = []
    if review_count > 0:
        from django.db.models import Count as _RCount
        dist_raw = dict(
            Review.objects.filter(course=course)
            .values_list('rating')
            .annotate(n=_RCount('id'))
            .values_list('rating', 'n')
        )
        for star in range(5, 0, -1):
            n = dist_raw.get(star, 0)
            pct = round(n / review_count * 100) if review_count else 0
            rating_distribution.append({'star': star, 'count': n, 'pct': pct})

    questions = CourseQuestion.objects.filter(
        course=course
    ).select_related('user').prefetch_related('answers__user').order_by('-created_at')

    is_course_teacher = request.user.is_authenticated and course.teacher_id == request.user.id

    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    total_minutes = CourseLesson.objects.filter(chapter__course=course).aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0
    student_count = Enrollment.objects.filter(course=course).count()

    completion_rate = None
    if student_count > 0 and total_lessons > 0:
        from django.db.models import Count as _Count
        completed_students = Enrollment.objects.filter(course=course).annotate(
            done=_Count(
                'student__lessonprogress',
                filter=Q(
                    student__lessonprogress__lesson__chapter__course=course,
                    student__lessonprogress__is_completed=True,
                )
            )
        ).filter(done__gte=total_lessons).count()
        completion_rate = round(completed_students / student_count * 100)

    related_courses = Course.objects.filter(
        is_published=True,
    ).exclude(id=course.id)
    if course.category:
        related_courses = related_courses.filter(category=course.category)
    related_courses = related_courses.select_related(
        'teacher', 'teacher__profile', 'category'
    ).annotate(
        _student_count=Count('enrollment', distinct=True),
    ).order_by('-_student_count')[:4]
    _attach_reviews(related_courses)

    from . import ai_assistant

    return render(request, 'main/course_detail.html', {
        'course': course,
        'platform_faqs': ai_assistant.PLATFORM_FAQS,
        'course_faqs': ai_assistant.build_course_faq(course),
        'already_purchased': already_purchased,
        'chapters': chapters,
        'reviews': reviews,
        'average_rating': average_rating,
        'review_count': review_count,
        'rating_distribution': rating_distribution,
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
        'completion_rate': completion_rate,
        'related_courses': related_courses,
        'is_preview': is_preview,
    })

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password']
                )
                Profile.objects.create(user=user, role='student')

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
        'error_message': error_message,
        'force_home_nav': True,
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

@require_student
def student_dashboard(request):
    total_minutes = LearningRecord.objects.filter(
        user=request.user
    ).aggregate(
        total=Sum('minutes')
    )['total'] or 0

    purchased_count = Enrollment.objects.filter(
        student=request.user
    ).count()

    from . import gamification
    gamification.evaluate_badges(request.user)
    badges = gamification.badge_progress(request.user)

    import datetime
    today = datetime.date.today()
    year_ago = today - datetime.timedelta(days=364)
    daily_records = (
        LearningRecord.objects.filter(
            user=request.user,
            watched_at__date__gte=year_ago,
        )
        .extra(select={'day': "DATE(watched_at)"})
        .values('day')
        .annotate(mins=Sum('minutes'))
        .order_by('day')
    )
    heatmap_data = {str(r['day']): r['mins'] for r in daily_records}
    import json as _json
    heatmap_json = _json.dumps(heatmap_data)

    return render(request, 'main/student_dashboard.html', {
        'total_minutes': total_minutes,
        'purchased_count': purchased_count,
        'current_streak': gamification.current_streak(request.user),
        'longest_streak': gamification.longest_streak(request.user),
        'badges': badges,
        'earned_badge_count': sum(1 for b in badges if b['earned']),
        'heatmap_json': heatmap_json,
        'heatmap_year_ago': year_ago.isoformat(),
        'heatmap_today': today.isoformat(),
    })

@require_teacher
def teacher_dashboard(request):
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

@require_teacher
def submit_marketing_request(request):

    initial = {}
    course_id = request.GET.get('course') or request.POST.get('course')
    if course_id and request.method == 'GET':
        try:
            course = Course.objects.get(id=course_id, teacher=request.user)
            initial['course'] = course
        except Course.DoesNotExist:
            pass

    if request.method == 'POST':
        form = MarketingRequestForm(request.POST, teacher=request.user)
        if form.is_valid():
            marketing_request = form.save(commit=False)
            marketing_request.teacher = request.user
            marketing_request.status = 'pending'
            marketing_request.save()

            Notification.objects.create(
                user=request.user,
                title='行銷申請已送出',
                content=f'您的課程「{marketing_request.course.title}」行銷申請已送出，等待後台處理。'
            )

            return redirect('marketing_requests')
    else:
        form = MarketingRequestForm(teacher=request.user, initial=initial)

    return render(request, 'main/marketing_request_form.html', {'form': form})

@require_teacher
def marketing_requests(request):

    requests = (
        MarketingRequest.objects
        .filter(teacher=request.user)
        .select_related('course')
        .order_by('-created_at')
    )
    return render(request, 'main/marketing_requests.html', {'marketing_requests': requests})

@login_required
def marketing_plan_detail(request, request_id):
    try:
        profile = request.user.profile
        if profile.role != 'teacher' and not profile.is_teacher:
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    mreq = get_object_or_404(
        MarketingRequest,
        id=request_id,
        teacher=request.user,
    )

    try:
        plan = mreq.plan
    except MarketingPlan.DoesNotExist:
        plan = None

    return render(request, 'main/marketing_plan_detail.html', {
        'marketing_request': mreq,
        'plan': plan,
    })

@login_required
def cancel_marketing_request(request, request_id):
    try:
        profile = request.user.profile
        if profile.role != 'teacher' and not profile.is_teacher:
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('home')

    mreq = get_object_or_404(
        MarketingRequest,
        id=request_id,
        teacher=request.user,
    )

    if request.method == 'POST' and mreq.status == 'pending':
        mreq.status = 'rejected'
        mreq.admin_note = '教師自行取消'
        mreq.save(update_fields=['status', 'admin_note', 'updated_at'])

        Notification.objects.create(
            user=request.user,
            title='行銷申請已取消',
            content=f'您的課程「{mreq.course.title}」行銷申請已取消。'
        )

    return redirect('marketing_requests')

@login_required
def request_vm_access(request):
    has_purchase = Enrollment.objects.filter(student=request.user).exists()
    if not has_purchase:
        return render(request, 'main/vm_request_form.html', {
            'form': None,
            'no_purchase': True,
        })

    if request.method == 'POST':
        form = VMAccessRequestForm(request.POST, student=request.user)
        if form.is_valid():
            vm_request = form.save(commit=False)
            vm_request.student = request.user
            vm_request.status = 'pending'
            vm_request.save()

            Notification.objects.create(
                user=request.user,
                title='虛擬機申請已送出',
                content=f'你申請的「{vm_request.course.title}」虛擬機使用申請已送出，等待管理員確認購課紀錄後核發。'
            )

            return redirect('my_vm_requests')
    else:
        form = VMAccessRequestForm(student=request.user)

    return render(request, 'main/vm_request_form.html', {'form': form})

@login_required
def my_vm_requests(request):
    vm_requests = VMAccessRequest.objects.filter(
        student=request.user
    ).select_related('course').order_by('-created_at')
    return render(request, 'main/vm_requests.html', {'vm_requests': vm_requests})

@login_required
def my_courses(request):
    try:
        request.user.profile
    except Profile.DoesNotExist:
        return redirect('home')

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
            total_lessons=Count('course__chapters__lessons', distinct=True),
            completed_lessons=Count(
                'course__learningrecord__lesson',
                filter=Q(
                    course__learningrecord__user=request.user,
                    course__learningrecord__lesson__isnull=False,
                ),
                distinct=True,
            ),
        )
    )

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
        total = enrollment.total_lessons
        enrollment.progress = (
            int(min(enrollment.completed_lessons, total) / total * 100) if total > 0 else 0
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

    quote = quote_basket(request.user, [course], selected_code)
    if quote.is_empty:
        return redirect('course_detail', course_id=course.id)

    error_message = quote.coupon_error
    success_message = (
        f'優惠券已套用，折抵 NT$ {quote.coupon_total}。' if quote.coupon_total > 0 else None
    )

    if action == 'buy' and not error_message:
        order = place_order(request.user, quote)
        return redirect('payment', order_id=order.id)

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

    if order.status != 'paid':
        return redirect('payment', order_id=order.id)

    payment_obj = order.payments.order_by('-id').first()
    items = order.items.select_related('course', 'course__teacher', 'course__teacher__profile').all()

    purchased_ids = set(Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True))
    cat_ids = [i.course.category_id for i in items if i.course.category_id]
    recommended_courses = (
        Course.objects.filter(is_published=True, category_id__in=cat_ids)
        .exclude(id__in=purchased_ids)
        .select_related('teacher', 'teacher__profile')
        .annotate(_pop=Count('enrollment', distinct=True))
        .order_by('-_pop')[:4]
    ) if cat_ids else Course.objects.none()

    return render(request, 'main/order_success.html', {
        'order': order,
        'payment': payment_obj,
        'items': items,
        'recommended_courses': recommended_courses,
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

    if not (enrolled or is_teacher or lesson.is_free_preview):
        return redirect('course_detail', course_id=course.id)

    chapters = course.chapters.prefetch_related('lessons').all()
    completed_ids = set(
        LearningRecord.objects.filter(user=request.user, course=course)
        .exclude(lesson=None).values_list('lesson_id', flat=True)
    )

    total_lessons = CourseLesson.objects.filter(chapter__course=course).count()
    done_count = len(completed_ids)
    progress = int(done_count / total_lessons * 100) if total_lessons else 0

    is_completed = lesson.id in completed_ids

    prog = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
    lesson_percent = prog.percent() if prog else 0
    resume_position = 0
    if prog:
        if prog.duration and prog.last_position < prog.duration - 3:
            resume_position = prog.last_position

    all_lessons = list(
        CourseLesson.objects.filter(chapter__course=course)
        .order_by('chapter__sort_order', 'sort_order')
        .values_list('id', flat=True)
    )
    curr_idx = all_lessons.index(lesson.id) if lesson.id in all_lessons else -1
    prev_lesson_id = all_lessons[curr_idx - 1] if curr_idx > 0 else None
    next_lesson_id = all_lessons[curr_idx + 1] if curr_idx >= 0 and curr_idx < len(all_lessons) - 1 else None

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
        'can_download_materials': enrolled or is_teacher,
        'lesson_percent': lesson_percent,
        'resume_position': resume_position,
        'prev_lesson_id': prev_lesson_id,
        'next_lesson_id': next_lesson_id,
    })

@login_required
def save_progress(request, lesson_id):
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

@require_teacher
def create_course(request):

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)

        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.is_published = False
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

def _notify_promotion_changes(course, old_discount, old_is_crowdfunding, old_early_bird):
    from .notifications import notify_followers

    messages = []
    if course.discount_price and (not old_discount or course.discount_price < old_discount):
        messages.append(f'折扣價 NT$ {course.discount_price}')
    if course.is_crowdfunding and not old_is_crowdfunding:
        messages.append('開啟募資開課')
    if course.early_bird_price and not old_early_bird:
        messages.append(f'早鳥優惠價 NT$ {course.early_bird_price}')

    if messages:
        notify_followers(
            course.teacher,
            f'課程優惠：{course.title}',
            f'{course.teacher.profile.display_name}老師的「{course.title}」推出'
            + '、'.join(messages) + '，把握機會！'
        )

@require_teacher
def edit_course(request, course_id):

    course = get_object_or_404(
        Course,
        id=course_id,
        teacher=request.user
    )

    if request.method == 'POST':
        old_discount = course.discount_price
        old_is_crowdfunding = course.is_crowdfunding
        old_early_bird = course.early_bird_price
        was_published = course.is_published

        form = CourseForm(
            request.POST,
            request.FILES,
            instance=course
        )

        if form.is_valid():
            course = form.save()
            if was_published:
                _notify_promotion_changes(
                    course, old_discount, old_is_crowdfunding, old_early_bird
                )
            return redirect('teacher_dashboard')

    else:
        form = CourseForm(instance=course)

    return render(request, 'main/edit_course.html', {
        'form': form,
        'course': course
    })

@require_teacher
def delete_course(request, course_id):

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
        'course_labels_json': course_labels,
        'course_minutes_json': course_minutes,
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
        'course_labels_json': course_labels,
        'purchase_counts_json': purchase_counts,
        'revenue_data_json': revenue_data,
        'watch_minutes_data_json': watch_minutes_data,
        'rating_data_json': rating_data,
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

    top_courses = (
        OrderItem.objects.filter(order__status='paid')
        .values('course__title')
        .annotate(gross=Sum('price'), purchases=Count('id'))
        .order_by('-gross')[:5]
    )
    top_course_labels = [t['course__title'] or '（課程已刪除）' for t in top_courses]
    top_course_revenue = [t['gross'] for t in top_courses]

    cat_dist = (
        Course.objects.filter(is_published=True)
        .values('category__name')
        .annotate(n=Count('id'))
        .order_by('-n')
    )
    cat_labels = [c['category__name'] or '未分類' for c in cat_dist]
    cat_counts = [c['n'] for c in cat_dist]

    method_dist = (
        Payment.objects.filter(status='paid')
        .values('method')
        .annotate(n=Count('id'))
        .order_by('-n')
    )
    method_display = dict(Payment.PAYMENT_METHOD_CHOICES)
    method_labels = [method_display.get(m['method'], m['method']) for m in method_dist]
    method_counts = [m['n'] for m in method_dist]

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
        'revenue_labels_json': revenue_labels,
        'revenue_series_json': revenue_series,
        'top_course_labels_json': top_course_labels,
        'top_course_revenue_json': top_course_revenue,
        'cat_labels_json': cat_labels,
        'cat_counts_json': cat_counts,
        'method_labels_json': method_labels,
        'method_counts_json': method_counts,
        'status_labels_json': status_labels,
        'status_counts_json': status_counts,
    })

def create_csv_response(filename):
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

@login_required
def add_to_cart(request, course_id):
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
    with_display_price([item.course for item in items])
    total = sum(item.course.display_price for item in items)

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
    if request.method != 'POST':
        return redirect('view_cart')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    courses = [item.course for item in cart.items.select_related('course').all()]

    quote = quote_basket(request.user, courses, request.POST.get('coupon_code', ''))
    if quote.is_empty:
        return redirect('view_cart')

    order = place_order(request.user, quote)
    cart.items.all().delete()

    return redirect('payment', order_id=order.id)

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
    return redirect('my_courses')

@login_required
def coupon_list(request):
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
    return redirect('view_cart')

def _require_course_teacher(request, course_id):
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

            from .notifications import notify_course_buyers
            notify_course_buyers(
                course,
                f'課程新影片：{course.title}',
                f'你購買的「{course.title}」新增了單元「{lesson.title}」，快去觀看！'
            )

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
        'materials': lesson.materials.all(),
        'material_form': LessonMaterialForm(),
    })

@login_required
def add_lesson_material(request, lesson_id):
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    course, redirect_resp = _require_course_teacher(request, lesson.chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        form = LessonMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.lesson = lesson
            if material.file:
                material.size_bytes = material.file.size
            material.save()

    return redirect('edit_lesson', lesson_id=lesson.id)

@login_required
def delete_material(request, material_id):
    material = get_object_or_404(LessonMaterial, id=material_id)
    lesson = material.lesson
    course, redirect_resp = _require_course_teacher(request, lesson.chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        material.delete()

    return redirect('edit_lesson', lesson_id=lesson.id)

@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(CourseLesson, id=lesson_id)
    course, redirect_resp = _require_course_teacher(request, lesson.chapter.course_id)
    if redirect_resp:
        return redirect_resp

    if request.method == 'POST':
        lesson.delete()

    return redirect('manage_content', course_id=course.id)

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

    is_teacher = (
        not request.user.is_superuser
        and refund.order.course
        and refund.order.course.teacher_id == request.user.id
    )
    if not (request.user.is_superuser or is_teacher):
        return redirect('home')

    if request.method == 'POST' and refund.status == 'pending':
        action = request.POST.get('action')
        if action == 'approve':
            approve_refund(refund)
        elif action == 'reject':
            reject_refund(refund)

    return redirect('manage_refunds')

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

@login_required
def add_question(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    is_teacher = course.teacher_id == request.user.id

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.user = request.user
            q.course = course
            q.title = (q.content or '')[:50]
            q.save()
            if not is_teacher:
                Notification.objects.create(
                    user=course.teacher,
                    title='課程有新提問',
                    content=f'課程「{course.title}」收到新的問題：{q.title}'
                )

                from . import ai_assistant
                if ai_assistant.auto_answer_question(q):
                    Notification.objects.create(
                        user=q.user,
                        title='AI 助教已回覆你的提問',
                        content=f'課程「{course.title}」中你的問題「{q.title}」已有 AI 助教的參考回覆，講師稍後仍會親自確認。'
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
            approve_course(audit.course, request.user, comment)
        elif action == 'reject':
            reject_course(audit.course, request.user, comment)

    return redirect('manage_audits')

def _require_teacher_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return None
    return profile if profile.role == 'teacher' else None

@login_required
def my_revenue(request):
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
def edit_bank_account(request):
    if not _require_teacher_profile(request):
        return redirect('home')

    bank_account, _ = TeacherBankAccount.objects.get_or_create(
        teacher=request.user,
        defaults={'bank_name': '', 'account_name': '', 'account_number': ''},
    )

    if request.method == 'POST':
        form = TeacherBankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            form.save()
            return redirect('my_withdrawals')
    else:
        form = TeacherBankAccountForm(instance=bank_account)

    return render(request, 'main/edit_bank_account.html', {'form': form})

@login_required
def my_withdrawals(request):
    if not _require_teacher_profile(request):
        return redirect('home')

    error = None
    bank_account = TeacherBankAccount.objects.filter(teacher=request.user).first()
    has_bank_account = bool(bank_account and bank_account.is_complete())

    if request.method == 'POST':
        if not has_bank_account:
            error = '請先綁定收款銀行帳戶，才能申請提領。'
        else:
            amount_raw = request.POST.get('amount', '').strip()
            try:
                amount = int(amount_raw)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                error = '請輸入正確的提領金額（正整數）。'
            else:
                withdrawal = WithdrawalRequest(
                    teacher=request.user,
                    amount=amount,
                    bank_info_snapshot=bank_account.snapshot_text(),
                )
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
        'bank_account': bank_account,
        'has_bank_account': has_bank_account,
    })

@login_required
def manage_withdrawals(request):
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
        action = request.POST.get('action')
        note = request.POST.get('note', '').strip()

        if action == 'complete':
            complete_withdrawal(withdrawal, note=note)
        elif action == 'reject':
            reject_withdrawal(withdrawal, note=note)

    return redirect('manage_withdrawals')

@login_required
def export_my_revenue_csv(request):
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

def _course_completion(user, course):
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

    _, _, is_complete = _course_completion(request.user, course)
    if not is_complete:
        return redirect('my_courses')

    issued_certificate, _ = CourseCertificate.objects.get_or_create(
        student=request.user,
        course=course,
    )
    pdf_bytes = render_certificate_pdf(issued_certificate)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f'eduflow-certificate-{issued_certificate.certificate_number}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def teacher_catalog(request):
    q = request.GET.get('q', '').strip()

    teacher_ids = (
        Course.objects.filter(is_published=True)
        .values_list('teacher_id', flat=True)
        .distinct()
    )
    teachers = User.objects.filter(id__in=teacher_ids).select_related('profile')
    if q:
        teachers = teachers.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )

    review_stats = Review.objects.filter(course__teacher=OuterRef('pk')).values('course__teacher')
    teachers = teachers.annotate(
        course_count=Count('course', filter=Q(course__is_published=True), distinct=True),
        student_count=Count('course__enrollment', distinct=True),
        avg_rating_raw=Subquery(
            review_stats.annotate(a=Avg('rating')).values('a')[:1],
            output_field=FloatField()),
    ).order_by('-course_count', '-student_count', 'username')

    teachers = list(teachers)
    for t in teachers:
        t.avg_rating = round(t.avg_rating_raw, 1) if t.avg_rating_raw else None

    return render(request, 'main/teacher_catalog.html', {
        'teachers': teachers,
        'q': q,
        'total_teachers': len(teachers),
    })

def teacher_profile(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)

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
        profile = teacher.profile
        role_display = profile.get_role_display()
    except Profile.DoesNotExist:
        profile = None
        role_display = ''

    is_owner = request.user.is_authenticated and request.user.id == teacher.id

    is_following = (
        request.user.is_authenticated
        and not is_owner
        and TeacherFollow.objects.filter(follower=request.user, teacher=teacher).exists()
    )
    follower_count = TeacherFollow.objects.filter(teacher=teacher).count()

    columns = TeacherColumn.objects.filter(teacher=teacher)
    articles = TeacherArticle.objects.filter(teacher=teacher).select_related('column')
    materials = TeacherMaterial.objects.filter(teacher=teacher)
    if not is_owner:
        columns = columns.filter(is_published=True)
        articles = articles.filter(is_published=True)
        materials = materials.filter(is_published=True)
    columns = list(columns)
    articles = list(articles)
    materials = list(materials)

    tab = request.GET.get('tab', 'course')
    if tab not in ('course', 'column', 'article', 'material'):
        tab = 'course'

    return render(request, 'main/teacher_profile.html', {
        'teacher': teacher,
        'profile': profile,
        'role_display': role_display,
        'courses': courses,
        'course_count': len(courses),
        'total_students': total_students,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'recent_reviews': recent_reviews,
        'is_owner': is_owner,
        'is_following': is_following,
        'follower_count': follower_count,
        'columns': columns,
        'articles': articles,
        'materials': materials,
        'column_count': len(columns),
        'article_count': len(articles),
        'material_count': len(materials),
        'active_tab': tab,
        'tabs': [
            ('course', '課程', len(courses)),
            ('column', '專欄', len(columns)),
            ('article', '文章', len(articles)),
            ('material', '教材', len(materials)),
        ],
    })

@login_required
def toggle_follow(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id)
    if request.method == 'POST' and teacher.id != request.user.id:
        existing = TeacherFollow.objects.filter(follower=request.user, teacher=teacher).first()
        if existing:
            existing.delete()
        else:
            TeacherFollow.objects.create(follower=request.user, teacher=teacher)
    default_url = reverse('teacher_profile', args=[teacher.id])
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(default_url)

@login_required
def my_following(request):
    follows = TeacherFollow.objects.filter(
        follower=request.user
    ).select_related('teacher', 'teacher__profile').order_by('-created_at')
    return render(request, 'main/my_following.html', {
        'follows': follows,
    })

def _require_teacher(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return None, redirect('home')
    if profile.role != 'teacher':
        return None, redirect('home')
    return profile, None

@login_required
def teacher_content(request):
    profile, redirect_resp = _require_teacher(request)
    if redirect_resp:
        return redirect_resp

    columns = TeacherColumn.objects.filter(teacher=request.user)
    articles = TeacherArticle.objects.filter(teacher=request.user).select_related('column')
    materials = TeacherMaterial.objects.filter(teacher=request.user)

    tab = request.GET.get('tab', 'column')
    if tab not in ('column', 'article', 'material'):
        tab = 'column'

    return render(request, 'main/teacher_content.html', {
        'columns': columns,
        'articles': articles,
        'materials': materials,
        'active_tab': tab,
        'tab_defs': [('column', '專欄'), ('article', '文章'), ('material', '教材')],
    })

@login_required
def add_column(request):
    profile, redirect_resp = _require_teacher(request)
    if redirect_resp:
        return redirect_resp
    if request.method == 'POST':
        form = ColumnForm(request.POST, request.FILES)
        if form.is_valid():
            column = form.save(commit=False)
            column.teacher = request.user
            column.save()
            return redirect('teacher_content')
    else:
        form = ColumnForm()
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '專欄', 'is_edit': False,
    })

@login_required
def edit_column(request, column_id):
    column = get_object_or_404(TeacherColumn, id=column_id, teacher=request.user)
    if request.method == 'POST':
        form = ColumnForm(request.POST, request.FILES, instance=column)
        if form.is_valid():
            form.save()
            return redirect('teacher_content')
    else:
        form = ColumnForm(instance=column)
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '專欄', 'is_edit': True,
    })

@login_required
def delete_column(request, column_id):
    column = get_object_or_404(TeacherColumn, id=column_id, teacher=request.user)
    if request.method == 'POST':
        column.delete()
    return redirect('teacher_content')

def column_detail(request, column_id):
    column = get_object_or_404(TeacherColumn, id=column_id)
    is_owner = request.user.is_authenticated and request.user.id == column.teacher_id
    if not column.is_published and not is_owner:
        raise Http404()
    articles = column.articles.all()
    if not is_owner:
        articles = articles.filter(is_published=True)
    has_access = column.has_access(request.user)
    return render(request, 'main/column_detail.html', {
        'column': column, 'articles': articles, 'is_owner': is_owner,
        'has_access': has_access,
    })

@login_required
def subscribe_column(request, column_id):
    column = get_object_or_404(TeacherColumn, id=column_id, is_published=True)
    if request.method != 'POST' or not column.is_paid or column.teacher_id == request.user.id:
        return redirect('column_detail', column_id=column.id)

    now = timezone.now()
    sub = ColumnSubscription.objects.filter(
        user=request.user, column=column, expires_at__gte=now
    ).order_by('-expires_at').first()
    base = sub.expires_at if sub else now
    new_expiry = base + timezone.timedelta(days=30)
    if sub:
        sub.expires_at = new_expiry
        sub.save(update_fields=['expires_at'])
    else:
        ColumnSubscription.objects.create(
            user=request.user, column=column, expires_at=new_expiry
        )

    Notification.objects.create(
        user=column.teacher,
        title='專欄有新訂閱',
        content=f'{request.user.profile.display_name} 訂閱了你的專欄「{column.title}」。'
    )
    return redirect('column_detail', column_id=column.id)

@login_required
def add_article(request):
    profile, redirect_resp = _require_teacher(request)
    if redirect_resp:
        return redirect_resp
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, teacher=request.user)
        if form.is_valid():
            article = form.save(commit=False)
            article.teacher = request.user
            article.save()
            return redirect('teacher_content')
    else:
        form = ArticleForm(teacher=request.user)
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '文章', 'is_edit': False,
    })

@login_required
def edit_article(request, article_id):
    article = get_object_or_404(TeacherArticle, id=article_id, teacher=request.user)
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article, teacher=request.user)
        if form.is_valid():
            form.save()
            return redirect('teacher_content')
    else:
        form = ArticleForm(instance=article, teacher=request.user)
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '文章', 'is_edit': True,
    })

@login_required
def delete_article(request, article_id):
    article = get_object_or_404(TeacherArticle, id=article_id, teacher=request.user)
    if request.method == 'POST':
        article.delete()
    return redirect('teacher_content')

def article_detail(request, article_id):
    article = get_object_or_404(
        TeacherArticle.objects.select_related('teacher', 'teacher__profile', 'column'),
        id=article_id,
    )
    is_owner = request.user.is_authenticated and request.user.id == article.teacher_id
    if not article.is_published and not is_owner:
        raise Http404()
    locked = bool(article.column and article.column.is_paid and not article.column.has_access(request.user))
    return render(request, 'main/article_detail.html', {
        'article': article, 'is_owner': is_owner, 'locked': locked,
    })

@login_required
def add_material(request):
    profile, redirect_resp = _require_teacher(request)
    if redirect_resp:
        return redirect_resp
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.teacher = request.user
            material.save()
            return redirect('teacher_content')
    else:
        form = MaterialForm()
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '教材', 'is_edit': False,
    })

@login_required
def edit_material(request, material_id):
    material = get_object_or_404(TeacherMaterial, id=material_id, teacher=request.user)
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            return redirect('teacher_content')
    else:
        form = MaterialForm(instance=material)
    return render(request, 'main/content_form.html', {
        'form': form, 'content_kind': '教材', 'is_edit': True,
    })

@login_required
def delete_material(request, material_id):
    material = get_object_or_404(TeacherMaterial, id=material_id, teacher=request.user)
    if request.method == 'POST':
        material.delete()
    return redirect('teacher_content')

@login_required
def ask_ai(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    is_teacher = course.teacher_id == request.user.id
    enrolled = Enrollment.objects.filter(course=course, student=request.user).exists()
    if not (is_teacher or enrolled or request.user.is_superuser):
        return JsonResponse({'ok': False, 'error': '購買本課程後即可使用 AI 助教。'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': '方法不允許。'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        question = payload.get('question', '')
        history = payload.get('history', [])
    except (ValueError, AttributeError):
        question = request.POST.get('question', '')
        history = []

    from . import ai_assistant

    faq = ai_assistant.match_platform_faq(question)
    if faq:
        return JsonResponse({
            'ok': True, 'answer': faq['answer'], 'faq': True, 'suggestions': [],
        })

    result = ai_assistant.answer_course_question(course, question, history=history)
    return JsonResponse(result)

@login_required
def ask_platform_ai(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': '方法不允許。'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        question = payload.get('question', '')
        history = payload.get('history', [])
    except (ValueError, AttributeError):
        question = request.POST.get('question', '')
        history = []

    from . import ai_assistant

    faq = ai_assistant.match_platform_faq(question)
    if faq:
        return JsonResponse({
            'ok': True, 'answer': faq['answer'], 'faq': True, 'suggestions': [],
        })

    result = ai_assistant.answer_platform_question(question, history=history)
    return JsonResponse(result)

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

    try:
        local_path = lesson.video_file.path
    except (NotImplementedError, ValueError):
        local_path = None
    if local_path:
        return _range_file_response(request, local_path)
    return redirect(lesson.video_file.url)

def serve_media(request, path):
    import os
    from django.conf import settings

    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    full = os.path.normpath(os.path.join(media_root, path))

    try:
        inside = os.path.commonpath([full, media_root]) == media_root
    except ValueError:
        inside = False
    if not inside or not os.path.isfile(full):
        raise Http404('media not found')

    rel = os.path.relpath(full, media_root).replace('\\', '/')
    if rel.startswith('course_videos/'):
        raise Http404('media not found')

    return _range_file_response(request, full)

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

def _group_cart_items_by_bundle(items):
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
    return profile.role == 'teacher' or profile.is_teacher

def _login_error_redirect(message):
    return redirect(f"{reverse('login')}?{urlencode({'error': message})}")

def _post_login_redirect(user):
    if user.is_superuser:
        return redirect('/admin/')
    return redirect('home')

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

            from .models import Enrollment as _Enrollment, TeacherFollow as _Follow
            from .notifications import notify_users
            audience = set(
                _Enrollment.objects.filter(course=course).values_list('student_id', flat=True)
            ) | set(
                _Follow.objects.filter(teacher=course.teacher).values_list('follower_id', flat=True)
            )
            notify_users(
                audience,
                f'課程新公告：{course.title}',
                f'「{course.title}」發布了新公告：{announcement.title}'
            )

    return redirect('manage_content', course_id=course.id)

@login_required
def add_bundle_to_cart(request, bundle_id):
    if request.method != 'POST':
        return redirect('view_cart')

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

def course_catalog(request):
    sort = request.GET.get('sort', 'newest')
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '').strip()

    qs = Course.objects.filter(is_published=True).select_related('teacher', 'teacher__profile', 'category')

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(teacher__username__icontains=q)
            | Q(teacher__first_name__icontains=q)
            | Q(teacher__last_name__icontains=q)
        )
    if cat:
        qs = qs.filter(category__name=cat)

    qs = qs.annotate(
        student_count=Count('enrollment', distinct=True),
        avg_rating_val=Avg('review__rating'),
    )

    sort_map = {
        'newest': '-created_at',
        'popular': '-student_count',
        'price_asc': 'price',
        'price_desc': '-price',
        'rating': '-avg_rating_val',
    }
    if sort not in sort_map:
        sort = 'newest'
    if sort == 'popular':
        qs = qs.order_by('-student_count', '-created_at')
    elif sort == 'rating':
        qs = qs.order_by(F('avg_rating_val').desc(nulls_last=True), '-created_at')
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
            ('rating', '評分最高'),
            ('price_asc', '價格低→高'),
            ('price_desc', '價格高→低'),
        ],
    })

@login_required
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

@require_teacher
def teacher_qna(request):

    questions = CourseQuestion.objects.filter(
        course__teacher=request.user
    ).select_related('user', 'course').prefetch_related('answers').annotate(
        human_answer_count=Count('answers', filter=Q(answers__is_ai_generated=False)),
        ai_answer_count=Count('answers', filter=Q(answers__is_ai_generated=True)),
    ).order_by('human_answer_count', '-created_at')

    return render(request, 'main/teacher_qna.html', {
        'questions': questions,
        'answer_form': AnswerForm(),
    })
