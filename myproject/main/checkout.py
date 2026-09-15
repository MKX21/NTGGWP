from dataclasses import dataclass, field, replace

from django.db import transaction
from django.utils import timezone

from .models import (
    Coupon,
    Enrollment,
    Order,
    OrderItem,
    Payment,
    Promotion,
)

@dataclass(frozen=True)
class QuoteLine:
    course: object
    list_price: int
    unit_price: int
    promo_discount: int
    coupon_discount: int
    paid_amount: int

    @property
    def discount_amount(self):
        return self.promo_discount + self.coupon_discount

@dataclass(frozen=True)
class Quote:
    lines: list = field(default_factory=list)
    list_total: int = 0
    subtotal: int = 0
    promo_total: int = 0
    coupon_total: int = 0
    total: int = 0
    coupon: object = None
    coupon_error: str = None

    @property
    def discount_total(self):
        return self.promo_total + self.coupon_total

    @property
    def is_empty(self):
        return not self.lines

def _allocate(total, weights):
    n = len(weights)
    if total <= 0 or n == 0:
        return [0] * n

    base = sum(weights)
    if base <= 0:
        return [0] * n
    if total >= base:
        return list(weights)

    exact = [total * w / base for w in weights]
    shares = [int(e) for e in exact]
    remainder = total - sum(shares)

    candidates = sorted(
        (i for i in range(n) if shares[i] < weights[i]),
        key=lambda i: exact[i] - shares[i],
        reverse=True,
    )
    for i in candidates[:remainder]:
        shares[i] += 1

    return shares

def _price_lines(courses, promo_map, coupon):
    raw = []
    for course in courses:
        unit_price = course.get_effective_price()
        promo = promo_map.get(course.id)
        promo_discount = promo.discount_for(unit_price) if promo else 0
        raw.append((course, unit_price, promo_discount))

    weights = [unit - promo for _, unit, promo in raw]
    promo_subtotal = sum(weights)
    coupon_total = coupon.discount_for(promo_subtotal) if coupon else 0
    shares = _allocate(coupon_total, weights)

    lines = [
        QuoteLine(
            course=course,
            list_price=course.price,
            unit_price=unit_price,
            promo_discount=promo_discount,
            coupon_discount=share,
            paid_amount=unit_price - promo_discount - share,
        )
        for (course, unit_price, promo_discount), share in zip(raw, shares)
    ]

    applied_coupon_total = sum(line.coupon_discount for line in lines)
    coupon_error = None
    if coupon is not None and applied_coupon_total <= 0:
        coupon_error = '此優惠券未達最低消費金額或無法套用。'

    return Quote(
        lines=lines,
        list_total=sum(line.list_price for line in lines),
        subtotal=sum(line.unit_price for line in lines),
        promo_total=sum(line.promo_discount for line in lines),
        coupon_total=applied_coupon_total,
        total=sum(line.paid_amount for line in lines),
        coupon=coupon if applied_coupon_total > 0 else None,
        coupon_error=coupon_error,
    )

def _active_promotion_map(courses):
    course_ids = {course.id for course in courses if course.id is not None}
    if not course_ids:
        return {}

    now = timezone.now()
    promotions = (
        Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
            courses__id__in=course_ids,
        )
        .prefetch_related('courses')
        .distinct()
        .order_by('created_at')
    )

    promo_map = {}
    for promo in promotions:
        for course in promo.courses.all():
            if course.id in course_ids:
                promo_map.setdefault(course.id, promo)
    return promo_map

def _resolve_coupon(coupon_code):
    code = (coupon_code or '').strip()
    if not code:
        return None, None

    coupon = Coupon.objects.filter(code__iexact=code).first()
    if coupon is None:
        return None, '找不到這張優惠券。'
    if not coupon.is_valid_now():
        return None, '這張優惠券目前不可使用。'
    return coupon, None

def _unpurchased(user, courses):
    courses = list(courses)
    if not courses:
        return []

    purchased_ids = set(
        Enrollment.objects.filter(student=user, course__in=courses)
        .values_list('course_id', flat=True)
    )
    return [course for course in courses if course.id not in purchased_ids]

def quote_basket(user, courses, coupon_code=''):
    remaining = _unpurchased(user, courses)
    coupon, coupon_error = _resolve_coupon(coupon_code)
    promo_map = _active_promotion_map(remaining)

    quote = _price_lines(remaining, promo_map, coupon)
    if coupon_error:
        quote = replace(quote, coupon=None, coupon_error=coupon_error)
    return quote

def with_display_price(courses):
    courses = list(courses)
    promo_map = _active_promotion_map(courses)

    for course in courses:
        unit_price = course.get_effective_price()
        promo = promo_map.get(course.id)
        course.display_price = unit_price - (promo.discount_for(unit_price) if promo else 0)
        course.display_has_discount = course.display_price < course.price
    return courses

def _find_pending_order(user, quote):
    wanted = sorted(line.course.id for line in quote.lines)
    coupon_id = quote.coupon.id if quote.coupon else None

    candidates = (
        Order.objects.filter(user=user, status='pending', final_price=quote.total)
        .prefetch_related('items')
    )
    for order in candidates:
        if order.coupon_id != coupon_id:
            continue
        if sorted(item.course_id for item in order.items.all()) == wanted:
            return order
    return None

@transaction.atomic
def place_order(user, quote):
    if quote.is_empty:
        raise ValueError('無法為空的報價成立訂單。')

    existing = _find_pending_order(user, quote)
    if existing is not None:
        return existing

    single_course = quote.lines[0].course if len(quote.lines) == 1 else None

    order = Order.objects.create(
        user=user,
        course=single_course,
        coupon=quote.coupon,
        original_price=quote.subtotal,
        discount_amount=quote.discount_total,
        final_price=quote.total,
        status='pending',
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            course=line.course,
            price=line.unit_price,
            discount_amount=line.discount_amount,
            paid_amount=line.paid_amount,
        )
        for line in quote.lines
    ])
    Payment.objects.create(
        order=order, amount=quote.total, status='pending', method='mock'
    )
    return order
