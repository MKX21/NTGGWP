"""結帳定價與下單的測試。

    python manage.py test main --settings=myproject.settings_test

前七個測試打的是 internal seam `checkout._price_lines` —— 純計算，用未存檔的
model 實例就能跑，不需要資料庫。後三個打對外 interface，需要資料庫。
"""
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .checkout import _price_lines, place_order, quote_basket
from .models import (
    Coupon,
    Course,
    CourseCategory,
    Enrollment,
    Notification,
    Order,
    OrderItem,
    Promotion,
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
        from .views import _finalize_paid_order

        order = place_order(self.user, quote_basket(self.user, [self.course_a]))
        self.assertFalse(
            Enrollment.objects.filter(student=self.user, course=self.course_a).exists()
        )

        _finalize_paid_order(order)
        order.refresh_from_db()

        self.assertEqual(order.status, 'paid')
        self.assertTrue(
            Enrollment.objects.filter(student=self.user, course=self.course_a).exists()
        )
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

        # 冪等：重複呼叫不會多開一次課、也不會多發一則通知
        _finalize_paid_order(order)
        self.assertEqual(
            Enrollment.objects.filter(student=self.user, course=self.course_a).count(), 1
        )
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
