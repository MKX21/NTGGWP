"""測試。

    python manage.py test main --settings=myproject.settings_test

分三部分：

* `PricingRuleTests` 打的是 internal seam `checkout._price_lines` —— 純計算，
  用未存檔的 model 實例就能跑，不需要資料庫。
* `QuoteBasketTests` 打結帳的對外 interface。
* 其餘類別是**回歸測試**：每一個都對應一個真實存在過的漏洞，
  註解說明它防的是什麼。
"""
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .checkout import _price_lines, place_order, quote_basket
from .models import (
    Cart,
    CartItem,
    Coupon,
    Course,
    CourseAudit,
    CourseCategory,
    CourseChapter,
    CourseLesson,
    Enrollment,
    Favorite,
    LearningRecord,
    Notification,
    Order,
    OrderItem,
    Payment,
    Profile,
    Promotion,
    Refund,
    Review,
)
from .transitions import approve_refund, fulfill_order


def make_course(price, discount_price=None, early_bird_price=None,
                is_crowdfunding=False, funding_days=30, pk=1):
    """未存檔的 Course，只用來餵純計算。"""
    now = timezone.now()
    return Course(
        id=pk,
        title=f'課程 {pk}',
        price=price,
        discount_price=discount_price,
        early_bird_price=early_bird_price,
        is_crowdfunding=is_crowdfunding,
        funding_start_date=now - timezone.timedelta(days=1) if is_crowdfunding else None,
        funding_end_date=now + timezone.timedelta(days=funding_days) if is_crowdfunding else None,
    )


def make_promotion(discount_type, discount_value):
    return Promotion(
        name='測試促銷', discount_type=discount_type, discount_value=discount_value,
        is_active=True,
        start_date=timezone.now() - timezone.timedelta(days=1),
        end_date=timezone.now() + timezone.timedelta(days=30),
    )


def make_coupon(discount_type, discount_value, min_spend=0):
    return Coupon(
        code='TEST', name='測試券', discount_type=discount_type,
        discount_value=discount_value, min_spend=min_spend,
        usage_limit=0, is_active=True,
        start_date=timezone.now() - timezone.timedelta(days=1),
        end_date=timezone.now() + timezone.timedelta(days=30),
    )


class PricingRuleTests(SimpleTestCase):
    """定價規則。不碰資料庫。"""

    def test_no_discount_pays_unit_price(self):
        quote = _price_lines([make_course(1800)], {}, None)

        self.assertEqual(quote.subtotal, 1800)
        self.assertEqual(quote.total, 1800)
        self.assertEqual(quote.discount_total, 0)

    def test_percent_promotion_applies_to_unit_price(self):
        course = make_course(1800)
        promo_map = {course.id: make_promotion('percent', 15)}

        quote = _price_lines([course], promo_map, None)

        self.assertEqual(quote.promo_total, 270)
        self.assertEqual(quote.total, 1530)

    def test_promotion_over_one_hundred_percent_cannot_go_negative(self):
        """discount_value=150（%）不該折出負數金額 —— 由疊加結構保證，不靠事後夾值。"""
        course = make_course(1000)
        promo_map = {course.id: make_promotion('percent', 150)}

        quote = _price_lines([course], promo_map, None)

        self.assertEqual(quote.promo_total, 1000)
        self.assertEqual(quote.total, 0)

    def test_coupon_min_spend_measured_after_promotion(self):
        """促銷後低於 min_spend → 券不生效，並回報原因。"""
        course = make_course(1000)
        promo_map = {course.id: make_promotion('percent', 50)}   # → 小計 500
        coupon = make_coupon('amount', 100, min_spend=600)

        quote = _price_lines([course], promo_map, coupon)

        self.assertEqual(quote.coupon_total, 0)
        self.assertIsNone(quote.coupon)
        self.assertIsNotNone(quote.coupon_error)
        self.assertEqual(quote.total, 500)

    def test_coupon_allocated_across_lines_sums_exactly(self):
        """最大餘額法：逐項 paid_amount 加總必須精確等於實付總額。"""
        courses = [
            make_course(1000, pk=1),
            make_course(1000, pk=2),
            make_course(1000, pk=3),
        ]
        coupon = make_coupon('amount', 100)

        quote = _price_lines(courses, {}, coupon)

        self.assertEqual(quote.coupon_total, 100)
        self.assertEqual(sum(line.coupon_discount for line in quote.lines), 100)
        self.assertEqual(sum(line.paid_amount for line in quote.lines), quote.total)
        self.assertEqual(quote.total, 2900)
        # 100 分給 3 項：34 / 33 / 33，不是 33/33/33 少了 1 元
        self.assertEqual(
            sorted(line.coupon_discount for line in quote.lines), [33, 33, 34]
        )

    def test_early_bird_and_promotion_stack(self):
        """募資期間的早鳥價之上，促銷再疊加（決策 4b）。"""
        course = make_course(2000, early_bird_price=1600, is_crowdfunding=True)
        promo_map = {course.id: make_promotion('percent', 10)}

        quote = _price_lines([course], promo_map, None)

        self.assertEqual(quote.subtotal, 1600)      # 售價＝早鳥價
        self.assertEqual(quote.promo_total, 160)    # 促銷作用於售價
        self.assertEqual(quote.total, 1440)

    def test_early_bird_ignored_outside_funding_window(self):
        """非募資課程的早鳥價不生效 —— get_effective_price 的 guard。"""
        course = make_course(2000, early_bird_price=1600, is_crowdfunding=False)

        quote = _price_lines([course], {}, None)

        self.assertEqual(quote.total, 2000)


class QuoteBasketTests(TestCase):
    """對外 interface。需要資料庫。"""

    def setUp(self):
        self.user = User.objects.create_user(username='student', password='x')
        self.teacher = User.objects.create_user(username='teacher', password='x')
        self.category = CourseCategory.objects.create(name='測試分類')
        self.course_a = Course.objects.create(
            title='A', teacher=self.teacher, category=self.category,
            price=1000, description='',
        )
        self.course_b = Course.objects.create(
            title='B', teacher=self.teacher, category=self.category,
            price=2000, description='',
        )

    def test_already_purchased_courses_are_excluded(self):
        Enrollment.objects.create(student=self.user, course=self.course_a)

        quote = quote_basket(self.user, [self.course_a, self.course_b])

        self.assertEqual([line.course.id for line in quote.lines], [self.course_b.id])
        self.assertEqual(quote.total, 2000)

    def test_place_order_is_idempotent(self):
        quote = quote_basket(self.user, [self.course_a])

        first = place_order(self.user, quote)
        second = place_order(self.user, quote_basket(self.user, [self.course_a]))

        self.assertEqual(first.id, second.id)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        self.assertEqual(OrderItem.objects.filter(order=first).count(), 1)

    def test_order_item_paid_amounts_sum_to_final_price(self):
        promo = Promotion.objects.create(
            name='促銷', discount_type='percent', discount_value=15,
            is_active=True,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=30),
        )
        promo.courses.set([self.course_a, self.course_b])
        Coupon.objects.create(
            code='SAVE100', name='折 100', discount_type='amount',
            discount_value=100, min_spend=0, usage_limit=0, is_active=True,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=30),
        )

        quote = quote_basket(self.user, [self.course_a, self.course_b], 'save100')
        order = place_order(self.user, quote)

        items = list(order.items.all())
        self.assertEqual(len(items), 2)
        self.assertEqual(sum(item.paid_amount for item in items), order.final_price)
        self.assertEqual(order.original_price, 3000)                 # Σ 售價
        self.assertEqual(order.discount_amount, 450 + 100)           # 促銷 + 券
        self.assertEqual(order.final_price, 2450)
        # price 保留購買當下售價，不含折扣
        self.assertEqual(sorted(item.price for item in items), [1000, 2000])
        self.assertEqual(order.payments.count(), 1)
        self.assertEqual(order.payments.first().amount, 2450)

    def test_place_order_then_finalize_enrolls_and_notifies(self):
        """seed_data 與付款流程共用的組合：成立訂單 → 付款成功 → 開通。"""
        from .transitions import fulfill_order

        order = place_order(self.user, quote_basket(self.user, [self.course_a]))
        self.assertFalse(
            Enrollment.objects.filter(student=self.user, course=self.course_a).exists()
        )

        fulfill_order(order)
        order.refresh_from_db()

        self.assertEqual(order.status, 'paid')
        self.assertTrue(
            Enrollment.objects.filter(student=self.user, course=self.course_a).exists()
        )
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

        # 冪等：重複呼叫不會多開一次課、也不會多發一則通知
        fulfill_order(order)
        self.assertEqual(
            Enrollment.objects.filter(student=self.user, course=self.course_a).count(), 1
        )
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)


# =========================================================================
# 以下為回歸測試：每一個都對應一個真實存在過的漏洞
# =========================================================================

class BaseFixture(TestCase):
    """共用的最小資料：一位學生、一位講師、一位管理員、一門已上架課程。"""

    def setUp(self):
        self.student = User.objects.create_user(username='student', password='pw')
        Profile.objects.create(user=self.student, role='student')

        self.teacher = User.objects.create_user(username='teacher', password='pw')
        Profile.objects.create(user=self.teacher, role='teacher')

        self.other = User.objects.create_user(username='other', password='pw')
        Profile.objects.create(user=self.other, role='student')

        self.admin = User.objects.create_superuser(username='admin', password='pw')

        self.category = CourseCategory.objects.create(name='分類')
        self.course = Course.objects.create(
            title='已上架課程', teacher=self.teacher, category=self.category,
            price=1000, description='', is_published=True,
        )
        self.chapter = CourseChapter.objects.create(course=self.course, title='第一章')
        self.lesson = CourseLesson.objects.create(
            chapter=self.chapter, title='第一單元', duration_minutes=10,
        )

    def buy(self, user, course):
        """走正式流程買一門課：成立訂單 → 付款完成 → 開通。

        付款那一步要自己標記 —— place_order 建立的 Payment 是 pending，
        真實流程由 views._mark_payment_paid 改成 paid 之後才呼叫 fulfill_order。
        """
        order = place_order(user, quote_basket(user, [course]))
        order.payments.update(status='paid', paid_at=timezone.now())
        fulfill_order(order)
        return order


class RefundRevokesAccessTests(BaseFixture):
    """漏洞：退款核准只改 Order.status，學生退了錢課還在。"""

    def setUp(self):
        super().setUp()
        self.order = self.buy(self.student, self.course)
        LearningRecord.objects.create(
            user=self.student, course=self.course, lesson=self.lesson, minutes=10)
        Review.objects.create(user=self.student, course=self.course, rating=5)
        self.refund = Refund.objects.create(
            order=self.order, user=self.student,
            amount=self.order.final_price, reason='測試', status='pending',
        )

    def test_approve_refund_revokes_enrollment_and_reverses_payment(self):
        approve_refund(self.refund)

        self.order.refresh_from_db()
        self.refund.refresh_from_db()
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.course).exists(),
            '退款後仍保有購課紀錄 —— 退了錢還能看課',
        )
        self.assertEqual(self.order.status, 'refunded')
        self.assertEqual(self.refund.status, 'completed')
        self.assertIsNotNone(self.refund.processed_at)
        self.assertEqual(
            list(self.order.payments.values_list('status', flat=True)), ['refunded'])

    def test_pending_payment_is_also_reversed(self):
        """換過付款方式而留下的 pending 付款，退款後不該變成孤兒。"""
        Payment.objects.create(
            order=self.order, amount=self.order.final_price,
            status='pending', method='atm',
        )

        approve_refund(self.refund)

        self.assertEqual(
            set(self.order.payments.values_list('status', flat=True)), {'refunded'})

    def test_approve_refund_keeps_learning_history_and_review(self):
        """撤銷的是存取權，不是歷史 —— 看過就是看過，評價不追溯竄改。"""
        approve_refund(self.refund)

        self.assertEqual(
            LearningRecord.objects.filter(user=self.student, course=self.course).count(), 1)
        self.assertEqual(
            Review.objects.filter(user=self.student, course=self.course).count(), 1)

    def test_approve_refund_is_idempotent(self):
        approve_refund(self.refund)
        n = Notification.objects.filter(user=self.student).count()

        approve_refund(self.refund)

        self.assertEqual(Notification.objects.filter(user=self.student).count(), n)


class AdminUsesSameTransitionTests(BaseFixture):
    """漏洞：admin 的 bulk action 是另一套狀態機，與前台行為不同。"""

    def _request(self):
        request = RequestFactory().post('/')
        request.user = self.admin
        request.session = 'session'
        request._messages = FallbackStorage(request)
        return request

    def test_admin_approve_refund_revokes_access_like_frontend(self):
        from .admin import RefundAdmin

        order = self.buy(self.student, self.course)
        refund = Refund.objects.create(
            order=order, user=self.student, amount=order.final_price,
            reason='測試', status='pending',
        )

        RefundAdmin(Refund, AdminSite()).approve_refund(
            self._request(), Refund.objects.filter(pk=refund.pk))

        refund.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(refund.status, 'completed')
        self.assertEqual(order.status, 'refunded')
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.course).exists(),
            '後台核准的退款沒有撤銷課程存取 —— 與前台行為分歧',
        )

    def test_admin_publish_goes_through_audit(self):
        """後台批次上架必須留下審核紀錄，不能是繞過 CourseAudit 的旁路。"""
        from .admin import CourseAdmin

        draft = Course.objects.create(
            title='草稿', teacher=self.teacher, category=self.category,
            price=500, description='', is_published=False,
        )

        CourseAdmin(Course, AdminSite()).make_published(
            self._request(), Course.objects.filter(pk=draft.pk))

        draft.refresh_from_db()
        self.assertTrue(draft.is_published)
        audit = CourseAudit.objects.filter(course=draft).first()
        self.assertIsNotNone(audit, '後台上架沒有留下審核紀錄')
        self.assertEqual(audit.status, 'approved')
        self.assertEqual(audit.reviewer, self.admin)
        self.assertTrue(
            Notification.objects.filter(user=self.teacher).exists(),
            '課程上架沒有通知講師',
        )


class UnpublishedCourseGateTests(BaseFixture):
    """漏洞：未上架/待審核的課程直接打網址就能瀏覽並購買。"""

    def setUp(self):
        super().setUp()
        self.draft = Course.objects.create(
            title='待審核課程', teacher=self.teacher, category=self.category,
            price=800, description='', is_published=False,
        )

    def test_public_cannot_see_unpublished_course(self):
        self.client.login(username='other', password='pw')
        self.assertEqual(
            self.client.get(reverse('course_detail', args=[self.draft.id])).status_code,
            404,
        )

    def test_teacher_can_preview_own_unpublished_course(self):
        self.client.login(username='teacher', password='pw')
        response = self.client.get(reverse('course_detail', args=[self.draft.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_preview'])

    def test_admin_can_preview_for_audit(self):
        """管理員必須看得到內容才能審核 —— 原本是盲審。"""
        self.client.login(username='admin', password='pw')
        self.assertEqual(
            self.client.get(reverse('course_detail', args=[self.draft.id])).status_code,
            200,
        )

    def test_enrolled_student_keeps_access_after_course_unpublished(self):
        """付過錢的人不該因為課程下架就吃 404。"""
        self.buy(self.student, self.course)
        self.course.is_published = False
        self.course.save()

        self.client.login(username='student', password='pw')
        self.assertEqual(
            self.client.get(reverse('course_detail', args=[self.course.id])).status_code,
            200,
        )

    def test_unpublished_course_cannot_be_checked_out(self):
        self.client.login(username='other', password='pw')
        self.assertEqual(
            self.client.get(reverse('checkout', args=[self.draft.id])).status_code, 404)

    def test_unpublished_course_cannot_be_added_to_cart(self):
        self.client.login(username='other', password='pw')
        self.assertEqual(
            self.client.post(reverse('add_to_cart', args=[self.draft.id])).status_code,
            404,
        )
        self.assertEqual(CartItem.objects.count(), 0)

    def test_even_teacher_cannot_purchase_own_unpublished_course(self):
        """預覽權不等於購買權。"""
        self.client.login(username='teacher', password='pw')
        self.assertEqual(
            self.client.get(reverse('checkout', args=[self.draft.id])).status_code, 404)


class VideoAuthorizationTests(BaseFixture):
    """漏洞：/media/course_videos/*.mp4 任何人知道網址就能直接下載。"""

    def test_non_enrolled_user_cannot_reach_video(self):
        self.client.login(username='other', password='pw')
        self.assertEqual(
            self.client.get(
                reverse('stream_lesson_video', args=[self.lesson.id])).status_code,
            404,
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('stream_lesson_video', args=[self.lesson.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_serve_media_refuses_course_videos(self):
        """即使 DEBUG 下掛載了 /media/，影片也不從那裡直出。"""
        from django.http import Http404

        from .views import serve_media

        request = RequestFactory().get('/media/course_videos/x.mp4')
        with self.assertRaises(Http404):
            serve_media(request, 'course_videos/x.mp4')


class StateChangingEndpointsTests(BaseFixture):
    """漏洞：四個會改資料庫的 endpoint 接受 GET（GET 不受 CSRF 保護）。"""

    def setUp(self):
        super().setUp()
        self.client.login(username='student', password='pw')

    def test_add_to_cart_ignores_get(self):
        self.client.get(reverse('add_to_cart', args=[self.course.id]))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_toggle_favorite_ignores_get(self):
        self.client.get(reverse('toggle_favorite', args=[self.course.id]))
        self.assertEqual(Favorite.objects.count(), 0)

    def test_remove_from_cart_ignores_get(self):
        cart = Cart.objects.create(user=self.student)
        item = CartItem.objects.create(cart=cart, course=self.course)

        self.client.get(reverse('remove_from_cart', args=[item.id]))

        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_claim_coupon_ignores_get(self):
        coupon = Coupon.objects.create(
            code='FREE', name='券', discount_type='amount', discount_value=50,
            min_spend=0, usage_limit=0, is_active=True,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=1),
        )

        self.client.get(reverse('claim_coupon', args=[coupon.id]))

        self.assertEqual(coupon.usercoupon_set.count(), 0)

    def test_post_still_works(self):
        """防的是 GET，正常的 POST 表單不能被誤傷。"""
        self.client.post(reverse('add_to_cart', args=[self.course.id]))
        self.assertEqual(CartItem.objects.count(), 1)


class OpenRedirectTests(BaseFixture):
    """漏洞：toggle_favorite 的 next 未經驗證就 redirect。"""

    def setUp(self):
        super().setUp()
        self.client.login(username='student', password='pw')

    def test_external_next_is_rejected(self):
        response = self.client.post(
            reverse('toggle_favorite', args=[self.course.id]),
            {'next': 'https://evil.example.com/phish'},
        )

        self.assertNotIn('evil.example.com', response.url)
        self.assertEqual(response.url, reverse('my_favorites'))

    def test_internal_next_is_honoured(self):
        target = reverse('course_detail', args=[self.course.id])

        response = self.client.post(
            reverse('toggle_favorite', args=[self.course.id]), {'next': target})

        self.assertEqual(response.url, target)


class PasswordResetFlowTests(TestCase):
    """漏洞：缺 password_reset_confirm，送出重設表單會 NoReverseMatch 500。"""

    def test_confirm_and_complete_urls_exist(self):
        self.assertTrue(
            reverse('password_reset_confirm', kwargs={'uidb64': 'MQ', 'token': 'a-b'}))
        self.assertTrue(reverse('password_reset_complete'))

    def test_submitting_reset_form_does_not_error(self):
        User.objects.create_user(
            username='someone', password='pw', email='someone@example.com')

        response = self.client.post(
            reverse('password_reset'), {'email': 'someone@example.com'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('password_reset_done'))
