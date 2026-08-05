from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),

    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/buy/', views.buy_course, name='buy_course'),
    path('course/<int:course_id>/checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/payment/', views.payment, name='payment'),
    path('order/<int:order_id>/success/', views.order_success, name='order_success'),
    path('course/<int:course_id>/purchase-success/', views.purchase_success, name='purchase_success'),
    path('course/<int:course_id>/watch/', views.watch_course, name='watch_course'),
    path('lesson/<int:lesson_id>/watch/', views.watch_lesson, name='watch_lesson'),
    path('lesson/<int:lesson_id>/progress/', views.save_progress, name='save_progress'),
    path('course/<int:course_id>/certificate/', views.certificate, name='certificate'),
    path('teacher/<int:teacher_id>/profile/', views.teacher_profile, name='teacher_profile'),

    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/analytics/', views.student_analytics, name='student_analytics'),

    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/analytics/', views.teacher_analytics, name='teacher_analytics'),
    path('teacher/qna/', views.teacher_qna, name='teacher_qna'),
    path('teacher/bank-account/', views.edit_bank_account, name='edit_bank_account'),

    path('export-data/', views.export_data_page, name='export_data_page'),
    path('analytics/', views.platform_analytics, name='platform_analytics'),
    path('export/courses.csv', views.export_courses_csv, name='export_courses_csv'),
    path('export/enrollments.csv', views.export_enrollments_csv, name='export_enrollments_csv'),
    path('export/learning-records.csv', views.export_learning_records_csv, name='export_learning_records_csv'),
    path('export/profiles.csv', views.export_profiles_csv, name='export_profiles_csv'),

    path('export/orders.csv', views.export_orders_csv, name='export_orders_csv'),
    path('export/order-items.csv', views.export_order_items_csv, name='export_order_items_csv'),
    path('export/payments.csv', views.export_payments_csv, name='export_payments_csv'),
    path('export/coupon-usage.csv', views.export_coupon_usage_csv, name='export_coupon_usage_csv'),
    path('export/reviews.csv', views.export_reviews_csv, name='export_reviews_csv'),
    path('export/course-lessons.csv', views.export_course_lessons_csv, name='export_course_lessons_csv'),

    path('register/', views.register, name='register'),
    path('register-success/', views.register_success, name='register_success'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # 快速登入（OAuth）
    path('oauth/google/login/', views.google_login, name='google_login'),
    path('oauth/google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('oauth/line/login/', views.line_login, name='line_login'),
    path('oauth/line/callback/', views.line_oauth_callback, name='line_oauth_callback'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('my-courses/', views.my_courses, name='my_courses'),

    # 購物車
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:course_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),

    # 收藏
    path('favorites/', views.my_favorites, name='my_favorites'),
    path('favorites/toggle/<int:course_id>/', views.toggle_favorite, name='toggle_favorite'),

    # 退款
    path('refunds/', views.my_refunds, name='my_refunds'),
    path('refunds/request/<int:order_id>/', views.request_refund, name='request_refund'),

    # 優惠券領取
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/claim/<int:coupon_id>/', views.claim_coupon, name='claim_coupon'),
    path('my-coupons/', views.my_coupons, name='my_coupons'),

    # A2 章節/單元管理
    path('course/<int:course_id>/content/', views.manage_content, name='manage_content'),
    path('content/chapter/add/<int:course_id>/', views.add_chapter, name='add_chapter'),
    path('content/chapter/<int:chapter_id>/edit/', views.edit_chapter, name='edit_chapter'),
    path('content/chapter/<int:chapter_id>/delete/', views.delete_chapter, name='delete_chapter'),
    path('content/lesson/add/<int:chapter_id>/', views.add_lesson, name='add_lesson'),
    path('content/lesson/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),
    path('content/lesson/<int:lesson_id>/delete/', views.delete_lesson, name='delete_lesson'),

    # A3 退款審核
    path('refunds/manage/', views.manage_refunds, name='manage_refunds'),
    path('refunds/<int:refund_id>/process/', views.process_refund, name='process_refund'),

    # A6 通知中心
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),

    # A7 課程問答
    path('course/<int:course_id>/question/add/', views.add_question, name='add_question'),
    path('question/<int:question_id>/answer/', views.add_answer, name='add_answer'),

    # A8 課程審核
    path('audits/manage/', views.manage_audits, name='manage_audits'),
    path('audits/<int:audit_id>/process/', views.process_audit, name='process_audit'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='main/password_reset.html'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='main/password_reset_done.html'
    ), name='password_reset_done'),
]