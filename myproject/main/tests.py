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
from django.core import mail
from django.core.exceptions import ValidationError
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
    CourseSplitSetting,
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
    RevenueRecord,
    Review,
    WithdrawalRequest,
)
from .transitions import (
    approve_refund,
    complete_withdrawal,
    fulfill_order,
    reject_withdrawal,
)


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


class RevenueSplitCalculationTests(SimpleTestCase):
    """RevenueRecord.recompute() 是純計算，未存檔的實例就能跑，不需要資料庫。"""

    def test_default_split_with_no_marketing_cost(self):
        record = RevenueRecord(
            gross_amount=1000, marketing_cost=0,
            teacher_split_percent=70, company_split_percent=30,
            teacher_marketing_share_percent=50, company_marketing_share_percent=50,
        )
        record.recompute()

        self.assertEqual(record.teacher_amount, 700)
        self.assertEqual(record.company_amount, 300)

    def test_marketing_cost_is_shared_by_its_own_ratio_not_the_split_ratio(self):
        """行銷成本負擔比例是獨立的一組比例，不該被誤用分潤比例去分攤成本。"""
        record = RevenueRecord(
            gross_amount=1000, marketing_cost=200,
            teacher_split_percent=70, company_split_percent=30,
            teacher_marketing_share_percent=50, company_marketing_share_percent=50,
        )
        record.recompute()

        # 毛額分潤：講師700 / 公司300；成本各半：講師100 / 公司100
        self.assertEqual(record.teacher_amount, 600)
        self.assertEqual(record.company_amount, 200)

    def test_amounts_always_sum_to_gross_minus_marketing_cost(self):
        """不管比例怎麼取整，兩邊加總都必須精確等於淨額，不能有錢憑空消失。"""
        for gross, cost, t_split, t_share in [
            (999, 137, 70, 50), (1, 0, 33, 10), (12345, 6789, 1, 99), (0, 0, 70, 50),
        ]:
            record = RevenueRecord(
                gross_amount=gross, marketing_cost=cost,
                teacher_split_percent=t_split, company_split_percent=100 - t_split,
                teacher_marketing_share_percent=t_share,
                company_marketing_share_percent=100 - t_share,
            )
            record.recompute()
            self.assertEqual(
                record.teacher_amount + record.company_amount, gross - cost,
                f'gross={gross} cost={cost} 兩邊加總對不上淨額',
            )

    def test_marketing_cost_larger_than_share_can_go_negative(self):
        """行銷成本異常偏高時如實呈現負值（該方倒貼），而不是報錯或被夾成 0。"""
        record = RevenueRecord(
            gross_amount=100, marketing_cost=1000,
            teacher_split_percent=70, company_split_percent=30,
            teacher_marketing_share_percent=50, company_marketing_share_percent=50,
        )
        record.recompute()

        self.assertEqual(record.teacher_amount, 70 - 500)
        self.assertEqual(record.company_amount, 30 - 500)


class CourseSplitSettingTests(TestCase):
    def test_for_course_falls_back_to_default_without_writing_a_row(self):
        teacher = User.objects.create_user(username='teacher', password='pw')
        course = Course.objects.create(title='課程', teacher=teacher, price=1000, description='')

        setting = CourseSplitSetting.for_course(course)

        self.assertEqual(setting.teacher_split_percent, 70)
        self.assertEqual(setting.company_split_percent, 30)
        self.assertEqual(setting.teacher_marketing_share_percent, 50)
        self.assertEqual(setting.company_marketing_share_percent, 50)
        self.assertIsNone(setting.pk)
        self.assertFalse(CourseSplitSetting.objects.filter(course=course).exists())

    def test_split_percents_must_sum_to_100(self):
        teacher = User.objects.create_user(username='teacher', password='pw')
        course = Course.objects.create(title='課程', teacher=teacher, price=1000, description='')
        setting = CourseSplitSetting(
            course=course, teacher_split_percent=80, company_split_percent=30,
        )

        with self.assertRaises(ValidationError):
            setting.clean()


class RevenueRecordFulfillmentTests(BaseFixture):
    """收支分潤紀錄要跟著 fulfill_order / approve_refund 這唯一的狀態轉換入口走。"""

    def test_fulfill_order_creates_revenue_record_with_default_split(self):
        order = self.buy(self.student, self.course)

        item = order.items.get()
        record = RevenueRecord.objects.get(order_item=item)
        self.assertEqual(record.course, self.course)
        self.assertEqual(record.teacher, self.teacher)
        self.assertEqual(record.gross_amount, item.paid_amount)
        self.assertEqual(record.teacher_split_percent, 70)
        self.assertEqual(record.status, 'confirmed')
        self.assertEqual(record.teacher_amount, round(item.paid_amount * 0.7))

    def test_custom_course_split_setting_is_snapshotted_at_creation(self):
        CourseSplitSetting.objects.create(
            course=self.course, teacher_split_percent=60, company_split_percent=40,
        )

        order = self.buy(self.student, self.course)

        record = RevenueRecord.objects.get(order_item=order.items.get())
        self.assertEqual(record.teacher_split_percent, 60)
        self.assertEqual(record.teacher_amount, round(order.final_price * 0.6))

    def test_fulfill_order_does_not_duplicate_revenue_record(self):
        order = self.buy(self.student, self.course)

        fulfill_order(order)  # 冪等：訂單已是 paid，重複呼叫不該重複建立

        self.assertEqual(
            RevenueRecord.objects.filter(order_item=order.items.get()).count(), 1)

    def test_approve_refund_reverses_revenue_record(self):
        order = self.buy(self.student, self.course)
        refund = Refund.objects.create(
            order=order, user=self.student, amount=order.final_price,
            reason='測試', status='pending',
        )

        approve_refund(refund)

        record = RevenueRecord.objects.get(order_item=order.items.get())
        self.assertEqual(record.status, 'reversed')
        self.assertIsNotNone(record.reversed_at)


class WithdrawalRequestTests(BaseFixture):
    def setUp(self):
        super().setUp()
        self.order = self.buy(self.student, self.course)
        self.record = RevenueRecord.objects.get(order_item=self.order.items.get())

    def test_available_balance_matches_confirmed_teacher_amount(self):
        self.assertEqual(
            WithdrawalRequest.available_balance(self.teacher), self.record.teacher_amount)

    def test_cannot_request_more_than_available_balance(self):
        with self.assertRaises(ValidationError):
            WithdrawalRequest.objects.create(
                teacher=self.teacher, amount=self.record.teacher_amount + 1)

    def test_pending_request_reserves_balance_against_a_second_request(self):
        WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)

        with self.assertRaises(ValidationError):
            WithdrawalRequest.objects.create(teacher=self.teacher, amount=1)

    def test_reversed_revenue_is_excluded_from_balance(self):
        """漏洞防範：課程被退款後，講師不該還能提領那筆已經沖銷的分潤。"""
        refund = Refund.objects.create(
            order=self.order, user=self.student, amount=self.order.final_price,
            reason='測試', status='pending',
        )
        approve_refund(refund)

        self.assertEqual(WithdrawalRequest.available_balance(self.teacher), 0)

    def test_complete_withdrawal_sets_processed_at_and_is_idempotent(self):
        withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)

        complete_withdrawal(withdrawal)
        n = Notification.objects.filter(user=self.teacher).count()
        complete_withdrawal(withdrawal)  # 冪等：已完成的不該重複發通知

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'completed')
        self.assertIsNotNone(withdrawal.processed_at)
        self.assertEqual(Notification.objects.filter(user=self.teacher).count(), n)

    def test_reject_withdrawal_frees_up_reserved_balance(self):
        withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)

        reject_withdrawal(withdrawal)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'rejected')
        self.assertEqual(
            WithdrawalRequest.available_balance(self.teacher), self.record.teacher_amount)


class RevenueAndWithdrawalViewTests(BaseFixture):
    """對外 view：講師查收支／申請提領，管理員後台審核。"""

    def setUp(self):
        super().setUp()
        self.order = self.buy(self.student, self.course)
        self.record = RevenueRecord.objects.get(order_item=self.order.items.get())

    def test_non_teacher_cannot_see_my_revenue(self):
        self.client.login(username='student', password='pw')

        response = self.client.get(reverse('my_revenue'))

        self.assertRedirects(response, reverse('home'))

    def test_teacher_sees_own_revenue_record(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('my_revenue'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, f'NT$ {self.record.teacher_amount}')

    def test_teacher_can_submit_withdrawal_request(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.post(
            reverse('my_withdrawals'), {'amount': self.record.teacher_amount})

        self.assertRedirects(response, reverse('my_withdrawals'))
        self.assertEqual(
            WithdrawalRequest.objects.filter(teacher=self.teacher).count(), 1)

    def test_withdrawal_request_over_balance_shows_error_and_is_not_created(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.post(
            reverse('my_withdrawals'), {'amount': self.record.teacher_amount + 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WithdrawalRequest.objects.count(), 0)
        self.assertContains(response, '超過可提領餘額')

    def test_non_superuser_cannot_reach_manage_withdrawals(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('manage_withdrawals'))

        self.assertRedirects(response, reverse('home'))

    def test_superuser_can_complete_withdrawal_via_view(self):
        withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)
        self.client.login(username='admin', password='pw')

        self.client.post(
            reverse('process_withdrawal', args=[withdrawal.id]), {'action': 'complete'})

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'completed')

    def test_process_withdrawal_ignores_get(self):
        """一致於其餘會改資料庫的 endpoint：GET 不受 CSRF 保護，不該被拿來核准提領。"""
        withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)
        self.client.login(username='admin', password='pw')

        self.client.get(reverse('process_withdrawal', args=[withdrawal.id]), {'action': 'complete'})

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'pending')


class WithdrawalNotificationEmailTests(BaseFixture):
    """管理員核准/拒絕提領時，講師要收到站內通知，有留 email 的話還要收到信。"""

    def setUp(self):
        super().setUp()
        self.order = self.buy(self.student, self.course)
        self.record = RevenueRecord.objects.get(order_item=self.order.items.get())
        self.teacher.email = 'teacher@example.com'
        self.teacher.save()
        self.withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)

    def test_complete_withdrawal_creates_notification_and_sends_email(self):
        complete_withdrawal(self.withdrawal)

        self.assertTrue(
            Notification.objects.filter(user=self.teacher, title='提領申請已完成').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.teacher.email, mail.outbox[0].to)
        self.assertIn('提領申請已完成', mail.outbox[0].subject)
        self.assertIn(str(self.withdrawal.amount), mail.outbox[0].body)

    def test_reject_withdrawal_email_includes_reason(self):
        reject_withdrawal(self.withdrawal, note='銀行帳號資料不符')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('銀行帳號資料不符', mail.outbox[0].body)

    def test_no_email_sent_when_teacher_has_no_email_but_notification_still_created(self):
        self.teacher.email = ''
        self.teacher.save()

        complete_withdrawal(self.withdrawal)

        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(
            Notification.objects.filter(user=self.teacher, title='提領申請已完成').exists())

    def test_idempotent_complete_does_not_resend_email(self):
        complete_withdrawal(self.withdrawal)
        complete_withdrawal(self.withdrawal)  # 已是 completed，第二次應該直接返回

        self.assertEqual(len(mail.outbox), 1)

    def test_admin_action_and_custom_view_share_the_same_email_behavior(self):
        """後台 django admin 的批次動作跟自訂 manage_withdrawals 頁面，
        都只是呼叫 transitions.complete_withdrawal，寄信行為不該有兩套。"""
        from .admin import WithdrawalRequestAdmin
        from .models import WithdrawalRequest as WR

        site = AdminSite()
        admin_instance = WithdrawalRequestAdmin(WR, site)
        request = RequestFactory().post('/admin/main/withdrawalrequest/')
        request.user = self.admin
        request.session = 'session'
        request._messages = FallbackStorage(request)

        admin_instance.mark_completed(request, WR.objects.filter(id=self.withdrawal.id))

        self.withdrawal.refresh_from_db()
        self.assertEqual(self.withdrawal.status, 'completed')
        self.assertEqual(len(mail.outbox), 1)


class RevenueAndWithdrawalCsvExportTests(BaseFixture):
    """收支紀錄／提領紀錄頁面的 CSV 匯出：權限、內容正確性、不能看到別人的資料。"""

    def setUp(self):
        super().setUp()
        self.order = self.buy(self.student, self.course)
        self.record = RevenueRecord.objects.get(order_item=self.order.items.get())
        self.withdrawal = WithdrawalRequest.objects.create(
            teacher=self.teacher, amount=self.record.teacher_amount)

        # 另一位講師的資料：確保匯出不會外洩非本人的收支/提領紀錄。
        self.other_teacher = User.objects.create_user(username='other_teacher', password='pw')
        Profile.objects.create(user=self.other_teacher, role='teacher')
        other_course = Course.objects.create(
            title='別人的課程', teacher=self.other_teacher, price=500, description='',
        )
        other_order = self.buy(self.other, other_course)
        self.other_record = RevenueRecord.objects.get(order_item=other_order.items.get())
        self.other_withdrawal = WithdrawalRequest.objects.create(
            teacher=self.other_teacher, amount=self.other_record.teacher_amount)

    def test_non_teacher_cannot_export_revenue_csv(self):
        self.client.login(username='student', password='pw')

        response = self.client.get(reverse('export_my_revenue_csv'))

        self.assertRedirects(response, reverse('home'))

    def test_non_teacher_cannot_export_withdrawals_csv(self):
        self.client.login(username='student', password='pw')

        response = self.client.get(reverse('export_my_withdrawals_csv'))

        self.assertRedirects(response, reverse('home'))

    def test_revenue_csv_contains_own_record_with_correct_content_type(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('export_my_revenue_csv'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        body = response.content.decode('utf-8-sig')
        self.assertIn(str(self.record.id), body)
        self.assertIn(self.course.title, body)
        self.assertIn(str(self.record.teacher_amount), body)

    def test_revenue_csv_excludes_other_teachers_records(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('export_my_revenue_csv'))

        body = response.content.decode('utf-8-sig')
        self.assertNotIn('別人的課程', body)
        self.assertNotIn(str(self.other_record.id) + ',', body)

    def test_withdrawals_csv_contains_own_request(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('export_my_withdrawals_csv'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode('utf-8-sig')
        self.assertIn(str(self.withdrawal.id), body)
        self.assertIn(str(self.withdrawal.amount), body)
        self.assertIn('待處理', body)

    def test_withdrawals_csv_excludes_other_teachers_requests(self):
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('export_my_withdrawals_csv'))

        body = response.content.decode('utf-8-sig')
        self.assertNotIn('other_teacher', body)

    def test_csv_has_exactly_one_bom_not_one_per_row(self):
        """漏洞：charset=utf-8-sig 時 HttpResponse 逐次 write() 各自編碼，
        csv.writer 每 writerow() 一次就多一個 BOM，Excel 開出來每一列都錯位。
        BOM 只能出現在檔案最開頭一次。"""
        self.client.login(username='teacher', password='pw')

        response = self.client.get(reverse('export_my_revenue_csv'))

        bom = '﻿'.encode('utf-8')
        self.assertEqual(response.content.count(bom), 1)
        self.assertTrue(response.content.startswith(bom))
        # 表頭緊接在 BOM 後面，中間不該夾著任何多餘的 BOM。
        self.assertTrue(response.content[len(bom):].startswith(b'record_id,'))
