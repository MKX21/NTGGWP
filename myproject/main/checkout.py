"""
結帳：定價與成立訂單
------------------------------------------------
這個 module 是「一次結帳要付多少錢」與「把它變成一張待付款訂單」的**唯一**答案。
單課直購與購物車結帳都只透過這裡，因此不可能算出兩種價格。

詞彙定義見專案根目錄 `CONTEXT.md`。折扣的疊加順序：

    售價  = Course.get_effective_price()   早鳥價或折扣價，二者取一
    小計  = 售價 − 促銷折扣                 促銷作用於售價
    實付  = 小計 − 優惠券折扣               優惠券作用於小計

每層作用於前一層的結果，所以折扣總額結構上不可能超過售價。

對外只有三個入口：

    quote_basket(user, courses, coupon_code)  算錢，回傳 Quote（不寫資料庫）
    place_order(user, quote)                  成立待付款訂單（原子性、冪等）
    with_display_price(courses)               批次掛上含促銷的顯示價

`_price_lines` 是 internal seam：純計算、不碰資料庫，供本 module 的測試直接
打規則用。**不要從 module 外面呼叫它** —— 它不做已購課過濾，也不驗證優惠券。

成立訂單不等於付款完成。開通課程是付款成功後的事，見 views._finalize_paid_order。
"""
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
    """報價中的一項課程。"""
    course: object
    list_price: int         # Course.price          定價
    unit_price: int         # get_effective_price() 售價
    promo_discount: int     # 促銷折扣
    coupon_discount: int    # 分攤到本項的優惠券折扣
    paid_amount: int        # unit_price − 兩層折扣

    @property
    def discount_amount(self):
        return self.promo_discount + self.coupon_discount


@dataclass(frozen=True)
class Quote:
    """一次結帳意圖的計算結果。尚未寫入資料庫。

    invariant：total == sum(line.paid_amount)，且 total >= 0。
    """
    lines: list = field(default_factory=list)
    list_total: int = 0      # Σ 定價
    subtotal: int = 0        # Σ 售價
    promo_total: int = 0
    coupon_total: int = 0
    total: int = 0           # 實付
    coupon: object = None    # 實際生效的優惠券；沒生效時為 None
    coupon_error: str = None # 券不生效的原因，供畫面顯示

    @property
    def discount_total(self):
        return self.promo_total + self.coupon_total

    @property
    def is_empty(self):
        return not self.lines


# =========================
# internal seam：純計算，不碰資料庫
# =========================

def _allocate(total, weights):
    """把 total 按 weights 比例分攤成整數，加總精確等於 total（最大餘額法）。

    先按比例向下取整，再把餘數依小數部分由大到小逐一補 1 元。
    只補給還有空間的項（floor < weight），避免分攤超過該項本身的金額。
    """
    n = len(weights)
    if total <= 0 or n == 0:
        return [0] * n

    base = sum(weights)
    if base <= 0:
        return [0] * n
    if total >= base:
        # 折扣已吃掉整個小計，逐項全額折抵
        return list(weights)

    exact = [total * w / base for w in weights]
    shares = [int(e) for e in exact]
    remainder = total - sum(shares)

    # 還有空間可補的項，依小數部分大者優先
    candidates = sorted(
        (i for i in range(n) if shares[i] < weights[i]),
        key=lambda i: exact[i] - shares[i],
        reverse=True,
    )
    for i in candidates[:remainder]:
        shares[i] += 1

    return shares


def _price_lines(courses, promo_map, coupon):
    """純計算報價。internal seam —— 不查資料庫、不過濾已購課、不驗證優惠券。

    courses   : Course 物件序列（可以是未存檔的實例）
    promo_map : {course_id: Promotion}，呼叫端已篩選過期間
    coupon    : Coupon 或 None，呼叫端已確認有效
    """
    raw = []
    for course in courses:
        unit_price = course.get_effective_price()
        promo = promo_map.get(course.id)
        promo_discount = promo.discount_for(unit_price) if promo else 0
        raw.append((course, unit_price, promo_discount))

    # 優惠券作用於「促銷後的小計」，再按各項促銷後金額比例分攤回去
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


# =========================
# 取值：把資料庫的東西撈齊，交給純計算
# =========================

def _active_promotion_map(courses):
    """{course_id: Promotion}，只含目前在期間內且有效的活動。

    固定 2 次查詢，不隨課程數成長。一堂課同時命中多個活動時取最先建立的那個。
    """
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
    """(coupon, error)。查不到或不可用時回傳 (None, 原因)。"""
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
    """濾掉使用者已經買過的課。一次查詢。"""
    courses = list(courses)
    if not courses:
        return []

    purchased_ids = set(
        Enrollment.objects.filter(student=user, course__in=courses)
        .values_list('course_id', flat=True)
    )
    return [course for course in courses if course.id not in purchased_ids]


# =========================
# 對外 interface
# =========================

def quote_basket(user, courses, coupon_code=''):
    """算出這個購物籃要付多少錢。不寫入任何資料。

    已購買的課程會被濾掉；全部都買過時回傳空報價（quote.is_empty 為 True）。
    優惠券無效時不套用，原因放在 quote.coupon_error。
    """
    remaining = _unpurchased(user, courses)
    coupon, coupon_error = _resolve_coupon(coupon_code)
    promo_map = _active_promotion_map(remaining)

    quote = _price_lines(remaining, promo_map, coupon)
    if coupon_error:
        quote = replace(quote, coupon=None, coupon_error=coupon_error)
    return quote


def with_display_price(courses):
    """批次掛上含促銷的顯示價，供列表頁與課程頁使用。

    掛兩個屬性：course.display_price（促銷後售價）、course.display_has_discount。
    固定查詢次數，不隨課程數成長 —— 不要在迴圈裡逐課呼叫。
    """
    courses = list(courses)
    promo_map = _active_promotion_map(courses)

    for course in courses:
        unit_price = course.get_effective_price()
        promo = promo_map.get(course.id)
        course.display_price = unit_price - (promo.discount_for(unit_price) if promo else 0)
        course.display_has_discount = course.display_price < course.price
    return courses


def _find_pending_order(user, quote):
    """找出內容相同的待付款訂單，讓重新整理不會重複下單。"""
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
    """把報價寫成一張待付款訂單：訂單 + 明細 + 付款紀錄，一起成功或一起失敗。

    冪等：同一使用者、同一組課程、同一張券、同一金額的待付款訂單已存在時，
    直接回傳既有訂單，不新建。
    """
    if quote.is_empty:
        raise ValueError('無法為空的報價成立訂單。')

    existing = _find_pending_order(user, quote)
    if existing is not None:
        return existing

    # 單課訂單沿用 Order.course（講師營收、退款入口等查詢仍依賴它）
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
