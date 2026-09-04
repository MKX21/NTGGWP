from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', '學生'),
        ('teacher', '老師'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="使用者")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="角色")
    avatar = models.ImageField(
        upload_to='avatars/', blank=True, null=True, verbose_name="大頭貼"
    )

    # 快速登入（OAuth）綁定用的第三方帳號 ID
    google_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, verbose_name="Google 帳號 ID"
    )
    line_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, verbose_name="LINE 帳號 ID"
    )

    # 單一帳號體系：is_teacher 由 Admin 後台賦予，具備教師權限後可在前台切換進教師專區，
    # 與既有 role（學生/老師二選一）並存，兩者的整合會在後續 Phase 處理。
    is_teacher = models.BooleanField(default=False, verbose_name="具備教師權限")

    bio = models.TextField(blank=True, null=True, verbose_name="講師簡介")

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = "使用者資料"
        verbose_name_plural = "使用者資料"


class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分類名稱")
    description = models.TextField(blank=True, null=True, verbose_name="分類說明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "課程分類"
        verbose_name_plural = "課程分類"


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', '初階'),
        ('intermediate', '中階'),
        ('advanced', '高階'),
    ]

    title = models.CharField(max_length=200, verbose_name="課程名稱")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="講師")
    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="課程分類"
    )
    price = models.IntegerField(verbose_name="價格")
    description = models.TextField(verbose_name="課程介紹")
    image = models.ImageField(
        upload_to='course_images/',
        verbose_name="課程圖片",
        blank=True,
        null=True
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner',
        verbose_name="課程難度"
    )
    is_published = models.BooleanField(default=True, verbose_name="是否上架")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    # 教師自訂折扣（任何課程皆可設定，不限募資課程）
    discount_price = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="折扣價（選填，需低於原價）"
    )

    # 募資開課
    is_crowdfunding = models.BooleanField(default=False, verbose_name="是否為募資課程")
    funding_goal = models.PositiveIntegerField(default=0, verbose_name="募資門檻人數")
    funding_start_date = models.DateTimeField(blank=True, null=True, verbose_name="募資開始時間")
    funding_end_date = models.DateTimeField(blank=True, null=True, verbose_name="募資結束時間")
    early_bird_price = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="早鳥優惠價（募資期間適用，需低於原價）"
    )

    # 分潤設定：Admin 於建立/編輯課程時以拉桿設定教師分潤比例，平台分潤 = 100 - 教師分潤
    teacher_revenue_share = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="教師分潤比例（%）"
    )

    # 宣傳影片意向：教師於新課程需求單或課程設定中標示，供行政人員後續安排
    PROMO_VIDEO_TYPE_CHOICES = [
        ('NONE', '未設定'),
        ('PHYSICAL_SHOOT', '實體拍攝'),
        ('AI_GENERATED', 'AI 形象廣告'),
    ]
    promo_video_type = models.CharField(
        max_length=20,
        choices=PROMO_VIDEO_TYPE_CHOICES,
        default='NONE',
        verbose_name="宣傳影片模式"
    )

    # 課程資訊卡：開課時間 / 觀看期限（僅顯示用，不做到期強制下架）
    start_date = models.DateTimeField(blank=True, null=True, verbose_name="開課時間")
    access_duration_days = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="觀看期限（天數，留空代表無限）"
    )

    # 課程介紹影片（頁面主視覺用，與 promo_video_type 不同：這是實際公開的影片素材）
    intro_video_url = models.URLField(blank=True, null=True, verbose_name="課程介紹影片連結")
    intro_video_file = models.FileField(
        upload_to='course_intro_videos/', blank=True, null=True, verbose_name="課程介紹影片檔"
    )

    def platform_revenue_share(self):
        """平台分潤比例（%），為 100 減去教師分潤比例。"""
        return 100 - self.teacher_revenue_share

    def __str__(self):
        return self.title

    def is_funding_active(self):
        if not self.is_crowdfunding or not self.funding_start_date or not self.funding_end_date:
            return False
        now = timezone.now()
        return self.funding_start_date <= now <= self.funding_end_date

    def funding_backers_count(self):
        return self.enrollment_set.count()

    def funding_progress_percent(self):
        if not self.funding_goal:
            return 0
        return min(100, round(self.funding_backers_count() / self.funding_goal * 100))

    def funding_is_goal_met(self):
        return self.funding_goal > 0 and self.funding_backers_count() >= self.funding_goal

    def funding_days_left(self):
        if not self.funding_end_date:
            return 0
        delta = self.funding_end_date - timezone.now()
        return max(0, delta.days)

    def get_effective_price(self):
        """目前實際售價：募資期間內優先用早鳥價，其次一般折扣價，否則原價。"""
        if self.is_crowdfunding and self.is_funding_active() and self.early_bird_price and self.early_bird_price < self.price:
            return self.early_bird_price
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def has_discount(self):
        return self.get_effective_price() < self.price

    class Meta:
        verbose_name = "課程"
        verbose_name_plural = "課程管理"


class CourseChapter(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="chapters",
        verbose_name="課程"
    )
    title = models.CharField(max_length=200, verbose_name="章節名稱")
    description = models.TextField(blank=True, null=True, verbose_name="章節說明")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="章節順序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        verbose_name = "課程章節"
        verbose_name_plural = "課程章節"
        ordering = ['course', 'sort_order']


class CourseLesson(models.Model):
    chapter = models.ForeignKey(
        CourseChapter,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="章節"
    )
    title = models.CharField(max_length=200, verbose_name="單元名稱")
    content = models.TextField(blank=True, null=True, verbose_name="單元內容")
    video_url = models.URLField(blank=True, null=True, verbose_name="影片連結")
    video_file = models.FileField(
        upload_to='course_videos/',
        blank=True,
        null=True,
        verbose_name="上傳影片檔"
    )
    duration_minutes = models.PositiveIntegerField(default=0, verbose_name="影片分鐘數")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="單元順序")
    is_free_preview = models.BooleanField(default=False, verbose_name="是否免費試看")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.chapter.title} - {self.title}"

    class Meta:
        verbose_name = "課程單元"
        verbose_name_plural = "課程單元"
        ordering = ['chapter', 'sort_order']


class CourseBundle(models.Model):
    """合購優惠組合：Admin 指定數門課程以合購價一起販售。"""
    name = models.CharField(max_length=200, verbose_name="合購名稱")
    description = models.TextField(blank=True, null=True, verbose_name="合購說明")
    courses = models.ManyToManyField(Course, related_name="bundles", verbose_name="包含課程")
    bundle_price = models.PositiveIntegerField(verbose_name="合購優惠價")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def total_individual_price(self):
        return sum(c.get_effective_price() for c in self.courses.all())

    def savings(self):
        return max(0, self.total_individual_price() - self.bundle_price)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "合購優惠組合"
        verbose_name_plural = "合購優惠組合"


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="學生")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name="購買時間")

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

    class Meta:
        verbose_name = "購課紀錄"
        verbose_name_plural = "購課紀錄"
        unique_together = ('student', 'course')


class LearningRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="觀看單元"
    )
    minutes = models.PositiveIntegerField(default=30, verbose_name="觀看分鐘數")
    watched_at = models.DateTimeField(auto_now_add=True, verbose_name="觀看時間")

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.minutes} 分鐘"

    class Meta:
        verbose_name = "學習紀錄"
        verbose_name_plural = "學習紀錄"


class LessonProgress(models.Model):
    """單元觀看進度：累積實際看過的秒數 + 續看位置（跨次保留）。"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, verbose_name="單元")
    # 每一秒是否看過的 bitmap（'0'/'1'），跨次累積、快轉跳過的秒不會被算入
    watched_map = models.TextField(blank=True, default='', verbose_name="已觀看秒圖")
    watched_seconds = models.PositiveIntegerField(default=0, verbose_name="累積觀看秒數")
    last_position = models.PositiveIntegerField(default=0, verbose_name="上次觀看位置(秒)")
    duration = models.PositiveIntegerField(default=0, verbose_name="影片總長(秒)")
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def percent(self):
        if self.duration <= 0:
            return 0
        return min(100, int(self.watched_seconds / self.duration * 100))

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} - {self.percent()}%"

    class Meta:
        verbose_name = "單元觀看進度"
        verbose_name_plural = "單元觀看進度"
        unique_together = ('user', 'lesson')


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('amount', '固定金額折扣'),
        ('percent', '百分比折扣'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="優惠碼")
    name = models.CharField(max_length=100, verbose_name="優惠券名稱")
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="折扣類型"
    )
    discount_value = models.PositiveIntegerField(verbose_name="折扣數值")
    min_spend = models.PositiveIntegerField(default=0, verbose_name="最低消費金額")
    start_date = models.DateTimeField(verbose_name="開始時間")
    end_date = models.DateTimeField(verbose_name="結束時間")
    usage_limit = models.PositiveIntegerField(default=0, verbose_name="總使用次數限制，0代表不限")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.code} - {self.name}"

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date > now:
            return False
        if self.end_date < now:
            return False
        if self.usage_limit > 0:
            used_count = self.usages.count()
            if used_count >= self.usage_limit:
                return False
        return True

    def is_expired(self):
        return timezone.now() > self.end_date

    def status_label(self):
        """後台/前台顯示用的目前狀態文字。"""
        now = timezone.now()
        if not self.is_active:
            return '已停用'
        if self.start_date > now:
            return '未開始'
        if self.end_date < now:
            return '已過期'
        if self.usage_limit > 0 and self.usages.count() >= self.usage_limit:
            return '已用完'
        return '使用中'

    def calculate_discount(self, price):
        # 期限/啟用/使用次數任一不符 → 一律 0 折扣（防止過期券被折抵）
        if not self.is_valid_now():
            return 0

        if price < self.min_spend:
            return 0

        if self.discount_type == 'amount':
            discount = self.discount_value
        elif self.discount_type == 'percent':
            discount = int(price * self.discount_value / 100)
        else:
            discount = 0

        if discount > price:
            discount = price

        return discount

    class Meta:
        verbose_name = "優惠券"
        verbose_name_plural = "優惠券管理"


class UserCoupon(models.Model):
    STATUS_CHOICES = [
        ('unused', '未使用'),
        ('used', '已使用'),
        ('expired', '已過期'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, verbose_name="優惠券")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unused',
        verbose_name="使用狀態"
    )
    received_at = models.DateTimeField(auto_now_add=True, verbose_name="領取時間")
    used_at = models.DateTimeField(blank=True, null=True, verbose_name="使用時間")

    def effective_status(self):
        """顯示用：尚未使用但券已過期 → 顯示已過期。"""
        if self.status == 'unused' and self.coupon.is_expired():
            return '已過期'
        return self.get_status_display()

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code} - {self.get_status_display()}"

    class Meta:
        verbose_name = "使用者優惠券"
        verbose_name_plural = "使用者優惠券"


class Promotion(models.Model):
    name = models.CharField(max_length=100, verbose_name="促銷活動名稱")
    description = models.TextField(blank=True, null=True, verbose_name="活動說明")
    discount_type = models.CharField(
        max_length=20,
        choices=Coupon.DISCOUNT_TYPE_CHOICES,
        verbose_name="折扣類型"
    )
    discount_value = models.PositiveIntegerField(verbose_name="折扣數值")
    start_date = models.DateTimeField(verbose_name="開始時間")
    end_date = models.DateTimeField(verbose_name="結束時間")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    courses = models.ManyToManyField(Course, blank=True, verbose_name="適用課程")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "促銷活動"
        verbose_name_plural = "促銷活動"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="使用者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def __str__(self):
        return f"{self.user.username} 的購物車"

    class Meta:
        verbose_name = "購物車"
        verbose_name_plural = "購物車"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="購物車"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="加入時間")
    bundle = models.ForeignKey(
        CourseBundle, on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name="所屬合購組合"
    )

    def __str__(self):
        return f"{self.cart.user.username} - {self.course.title}"

    class Meta:
        verbose_name = "購物車明細"
        verbose_name_plural = "購物車明細"
        unique_together = ('cart', 'course')


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '已付款'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="購買者")
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="課程"
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="使用優惠券"
    )
    original_price = models.PositiveIntegerField(verbose_name="原價")
    discount_amount = models.PositiveIntegerField(default=0, verbose_name="折扣金額")
    final_price = models.PositiveIntegerField(verbose_name="實付金額")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='paid',
        verbose_name="訂單狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        course_title = self.course.title if self.course else "多課程訂單"
        return f"{self.user.username} - {course_title} - NT$ {self.final_price}"

    class Meta:
        verbose_name = "訂單"
        verbose_name_plural = "訂單管理"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="訂單"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    price = models.PositiveIntegerField(verbose_name="購買當下價格")
    discount_amount = models.PositiveIntegerField(default=0, verbose_name="此項折扣金額")
    paid_amount = models.PositiveIntegerField(default=0, verbose_name="此項實付金額")

    def __str__(self):
        return f"{self.order.id} - {self.course.title}"

    class Meta:
        verbose_name = "訂單明細"
        verbose_name_plural = "訂單明細"


class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="usages",
        verbose_name="優惠券"
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, verbose_name="訂單")
    discount_amount = models.PositiveIntegerField(verbose_name="實際折扣金額")
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="使用時間")

    def __str__(self):
        return f"{self.user.username} 使用 {self.coupon.code}"

    class Meta:
        verbose_name = "優惠券使用紀錄"
        verbose_name_plural = "優惠券使用紀錄"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', '信用卡'),
        ('atm', 'ATM 虛擬帳號轉帳'),
        ('cvs', '超商代碼繳費'),
        ('line_pay', 'LINE Pay'),
        ('cash', '現金'),
        ('mock', '模擬付款'),
    ]

    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '付款成功'),
        ('failed', '付款失敗'),
        ('refunded', '已退款'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="訂單"
    )
    method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default='mock',
        verbose_name="付款方式"
    )
    amount = models.PositiveIntegerField(verbose_name="付款金額")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='paid',
        verbose_name="付款狀態"
    )
    transaction_no = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="交易編號"
    )
    # 模擬金流用（未來串接真金流時由 gateway 回傳填入）
    virtual_account = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="ATM 虛擬帳號"
    )
    payment_code = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="超商繳費代碼"
    )
    expire_at = models.DateTimeField(blank=True, null=True, verbose_name="繳費期限")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="付款時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"訂單 {self.order.id} - NT$ {self.amount} - {self.get_status_display()}"

    class Meta:
        verbose_name = "付款紀錄"
        verbose_name_plural = "付款紀錄"


class Refund(models.Model):
    STATUS_CHOICES = [
        ('pending', '退款審核中'),
        ('approved', '退款通過'),
        ('rejected', '退款拒絕'),
        ('completed', '退款完成'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="refunds",
        verbose_name="訂單"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="申請者")
    amount = models.PositiveIntegerField(verbose_name="退款金額")
    reason = models.TextField(verbose_name="退款原因")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="退款狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="處理時間")

    def __str__(self):
        return f"{self.user.username} - 訂單 {self.order.id} - {self.get_status_display()}"

    class Meta:
        verbose_name = "退款紀錄"
        verbose_name_plural = "退款紀錄"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏時間")

    def __str__(self):
        return f"{self.user.username} 收藏 {self.course.title}"

    class Meta:
        verbose_name = "收藏課程"
        verbose_name_plural = "收藏課程"
        unique_together = ('user', 'course')


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="評論者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="評分")
    comment = models.TextField(blank=True, null=True, verbose_name="評論內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="評論時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating} 星"

    class Meta:
        verbose_name = "課程評價"
        verbose_name_plural = "課程評價"
        unique_together = ('user', 'course')


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="接收者")
    title = models.CharField(max_length=200, verbose_name="通知標題")
    content = models.TextField(verbose_name="通知內容")
    is_read = models.BooleanField(default=False, verbose_name="是否已讀")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"


class CourseQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="提問者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    lesson = models.ForeignKey(
        CourseLesson,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="相關單元"
    )
    title = models.CharField(max_length=200, verbose_name="問題標題")
    content = models.TextField(verbose_name="問題內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="提問時間")

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        verbose_name = "課程問答"
        verbose_name_plural = "課程問答"


class CourseAnswer(models.Model):
    question = models.ForeignKey(
        CourseQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="問題"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="回答者")
    content = models.TextField(verbose_name="回答內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="回答時間")

    def __str__(self):
        return f"{self.question.title} - {self.user.username}"

    class Meta:
        verbose_name = "課程回答"
        verbose_name_plural = "課程回答"


class CourseAnnouncement(models.Model):
    """課程公告：教師（本人課程）或 Admin 可發布，僅已購買學員/該課程教師/Admin 看得到。"""
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="announcements", verbose_name="課程"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="發布者")
    title = models.CharField(max_length=200, verbose_name="公告標題")
    content = models.TextField(verbose_name="公告內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="發布時間")

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        verbose_name = "課程公告"
        verbose_name_plural = "課程公告"
        ordering = ['-created_at']


class CourseComment(models.Model):
    """課程留言區：開放任何登入使用者留言，與需購買才能發問的課程問答區區隔。"""
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="comments", verbose_name="課程"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="留言者")
    content = models.TextField(verbose_name="留言內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="留言時間")

    def __str__(self):
        return f"{self.course.title} - {self.user.username}"

    class Meta:
        verbose_name = "課程留言"
        verbose_name_plural = "課程留言"
        ordering = ['-created_at']


class CourseAudit(models.Model):
    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '審核通過'),
        ('rejected', '審核退回'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="審核人員"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="審核狀態"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="審核意見")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="送審時間")
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="審核時間")

    def __str__(self):
        return f"{self.course.title} - {self.get_status_display()}"

    class Meta:
        verbose_name = "課程審核"
        verbose_name_plural = "課程審核"


class TeacherBankAccount(models.Model):
    """教師收款銀行帳戶（一位教師一組，提領申請時會存快照，不受後續修改影響）。"""
    teacher = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="bank_account", verbose_name="教師"
    )
    bank_name = models.CharField(max_length=100, verbose_name="銀行名稱")
    bank_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="銀行代碼")
    branch_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="分行名稱")
    account_name = models.CharField(max_length=100, verbose_name="戶名")
    account_number = models.CharField(max_length=50, verbose_name="帳號")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def __str__(self):
        return f"{self.teacher.username} - {self.bank_name} {self.account_number}"

    class Meta:
        verbose_name = "教師銀行帳戶"
        verbose_name_plural = "教師銀行帳戶"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', '審核中'),
        ('APPROVED', '已核准'),
        ('REJECTED', '已拒絕'),
    ]

    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="withdrawal_requests", verbose_name="教師"
    )
    amount = models.PositiveIntegerField(verbose_name="提領金額")
    bank_info_snapshot = models.TextField(verbose_name="銀行帳戶快照（申請當下）")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="審核狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="處理時間")

    def __str__(self):
        return f"{self.teacher.username} - NT$ {self.amount} - {self.get_status_display()}"

    class Meta:
        verbose_name = "提領申請"
        verbose_name_plural = "提領申請"
        ordering = ['-created_at']