import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
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

    google_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, verbose_name="Google 帳號 ID"
    )
    line_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, verbose_name="LINE 帳號 ID"
    )

    is_teacher = models.BooleanField(default=False, verbose_name="具備教師權限")

    bio = models.TextField(blank=True, null=True, verbose_name="講師簡介")

    cover_image = models.ImageField(
        upload_to='teacher_covers/', blank=True, null=True, verbose_name="講師頁封面"
    )
    headline = models.CharField(
        max_length=100, blank=True, default='', verbose_name="講師稱號"
    )
    facebook_url = models.URLField(blank=True, default='', verbose_name="Facebook 連結")
    youtube_url = models.URLField(blank=True, default='', verbose_name="YouTube 連結")

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def follower_count(self):
        return self.user.followers.count()

    @property
    def display_name(self):
        full = f"{self.user.last_name}{self.user.first_name}".strip()
        return full or self.user.username

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

    discount_price = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="折扣價（選填，需低於原價）"
    )

    is_crowdfunding = models.BooleanField(default=False, verbose_name="是否為募資課程")
    funding_goal = models.PositiveIntegerField(default=0, verbose_name="募資門檻人數")
    funding_start_date = models.DateTimeField(blank=True, null=True, verbose_name="募資開始時間")
    funding_end_date = models.DateTimeField(blank=True, null=True, verbose_name="募資結束時間")
    early_bird_price = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="早鳥優惠價（募資期間適用，需低於原價）"
    )

    teacher_revenue_share = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="教師分潤比例（%）"
    )

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

    start_date = models.DateTimeField(blank=True, null=True, verbose_name="開課時間")
    access_duration_days = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="觀看期限（天數，留空代表無限）"
    )

    intro_video_url = models.URLField(blank=True, null=True, verbose_name="課程介紹影片連結")
    intro_video_file = models.FileField(
        upload_to='course_intro_videos/', blank=True, null=True, verbose_name="課程介紹影片檔"
    )

    def platform_revenue_share(self):
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

class LessonMaterial(models.Model):
    TYPE_CHOICES = [
        ('slides', '簡報'),
        ('practice', '練習檔'),
        ('reading', '延伸閱讀'),
        ('other', '其他'),
    ]

    lesson = models.ForeignKey(
        CourseLesson, on_delete=models.CASCADE, related_name="materials", verbose_name="單元"
    )
    title = models.CharField(max_length=200, verbose_name="教材名稱")
    material_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='slides', verbose_name="教材類型"
    )
    file = models.FileField(upload_to='lesson_materials/', verbose_name="檔案")
    size_bytes = models.PositiveBigIntegerField(default=0, verbose_name="檔案大小(bytes)")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="排序")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="上傳時間")

    def filename(self):
        import os
        return os.path.basename(self.file.name)

    def icon_class(self):
        name = self.filename().lower()
        ext = name.rsplit('.', 1)[-1] if '.' in name else ''
        return {
            'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint',
            'doc': 'fa-file-word', 'docx': 'fa-file-word',
            'pdf': 'fa-file-pdf',
            'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel', 'csv': 'fa-file-csv',
            'zip': 'fa-file-zipper', 'rar': 'fa-file-zipper', '7z': 'fa-file-zipper',
            'jpg': 'fa-file-image', 'jpeg': 'fa-file-image', 'png': 'fa-file-image', 'gif': 'fa-file-image',
            'mp4': 'fa-file-video', 'mp3': 'fa-file-audio',
            'txt': 'fa-file-lines',
        }.get(ext, 'fa-file')

    def size_display(self):
        b = self.size_bytes or 0
        if b <= 0:
            return ''
        for unit in ['B', 'KB', 'MB', 'GB']:
            if b < 1024:
                return f'{b:.0f} {unit}' if unit == 'B' else f'{b:.1f} {unit}'
            b /= 1024
        return f'{b:.1f} TB'

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

    class Meta:
        verbose_name = "單元教材"
        verbose_name_plural = "單元教材"
        ordering = ['lesson', 'sort_order', 'id']

class CourseBundle(models.Model):
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程")
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, verbose_name="單元")
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


class CourseCertificate(models.Model):
    certificate_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="證書編號",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_certificates",
        verbose_name="學生",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="課程",
    )
    issued_at = models.DateTimeField(auto_now_add=True, verbose_name="核發時間")

    @property
    def display_number(self):
        return f"EDUFLOW-{str(self.certificate_number).upper()}"

    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.display_number}"

    class Meta:
        verbose_name = "課程結業證書"
        verbose_name_plural = "課程結業證書"
        ordering = ('-issued_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'course'),
                name='unique_student_course_certificate',
            ),
        ]

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

    def discount_for(self, price):
        if price < self.min_spend:
            return 0

        if self.discount_type == 'amount':
            discount = self.discount_value
        elif self.discount_type == 'percent':
            discount = int(price * self.discount_value / 100)
        else:
            discount = 0

        return min(discount, price)

    def calculate_discount(self, price):
        if not self.is_valid_now():
            return 0
        return self.discount_for(price)

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

    def is_active_now(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def discount_for(self, price):
        if self.discount_type == 'amount':
            discount = self.discount_value
        elif self.discount_type == 'percent':
            discount = int(price * self.discount_value / 100)
        else:
            discount = 0

        return min(discount, price)

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
        default='pending',
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
        default='pending',
        verbose_name="付款狀態"
    )
    transaction_no = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="交易編號"
    )
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
    is_ai_generated = models.BooleanField(default=False, verbose_name="AI 自動回答")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="回答時間")

    def __str__(self):
        return f"{self.question.title} - {self.user.username}"

    class Meta:
        verbose_name = "課程回答"
        verbose_name_plural = "課程回答"

class CourseAnnouncement(models.Model):
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

class CourseSplitSetting(models.Model):
    DEFAULT_TEACHER_SPLIT_PERCENT = 70
    DEFAULT_COMPANY_SPLIT_PERCENT = 30
    DEFAULT_TEACHER_MARKETING_SHARE_PERCENT = 50
    DEFAULT_COMPANY_MARKETING_SHARE_PERCENT = 50

    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        related_name="split_setting",
        verbose_name="課程"
    )
    teacher_split_percent = models.PositiveSmallIntegerField(
        default=DEFAULT_TEACHER_SPLIT_PERCENT, verbose_name="講師分潤比例(%)"
    )
    company_split_percent = models.PositiveSmallIntegerField(
        default=DEFAULT_COMPANY_SPLIT_PERCENT, verbose_name="公司分潤比例(%)"
    )
    teacher_marketing_share_percent = models.PositiveSmallIntegerField(
        default=DEFAULT_TEACHER_MARKETING_SHARE_PERCENT, verbose_name="講師負擔行銷成本比例(%)"
    )
    company_marketing_share_percent = models.PositiveSmallIntegerField(
        default=DEFAULT_COMPANY_MARKETING_SHARE_PERCENT, verbose_name="公司負擔行銷成本比例(%)"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def clean(self):
        if self.teacher_split_percent + self.company_split_percent != 100:
            raise ValidationError('講師分潤比例 + 公司分潤比例必須等於 100')
        if self.teacher_marketing_share_percent + self.company_marketing_share_percent != 100:
            raise ValidationError('講師行銷成本負擔比例 + 公司行銷成本負擔比例必須等於 100')

    @classmethod
    def for_course(cls, course):
        return cls.objects.filter(course=course).first() or cls(course=course)

    def __str__(self):
        return f"{self.course.title} - 講師{self.teacher_split_percent}% / 公司{self.company_split_percent}%"

    class Meta:
        verbose_name = "課程分潤設定"
        verbose_name_plural = "課程分潤設定"

class RevenueRecord(models.Model):
    STATUS_CHOICES = [
        ('confirmed', '已確認'),
        ('reversed', '已沖銷（退款）'),
    ]

    order_item = models.OneToOneField(
        OrderItem, on_delete=models.CASCADE, related_name="revenue_record", verbose_name="訂單明細"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="revenue_records", verbose_name="訂單"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="revenue_records", verbose_name="課程"
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="revenue_records", verbose_name="講師"
    )

    gross_amount = models.PositiveIntegerField(verbose_name="實付金額")
    marketing_cost = models.PositiveIntegerField(default=0, verbose_name="行銷成本")

    teacher_split_percent = models.PositiveSmallIntegerField(verbose_name="講師分潤比例(%)")
    company_split_percent = models.PositiveSmallIntegerField(verbose_name="公司分潤比例(%)")
    teacher_marketing_share_percent = models.PositiveSmallIntegerField(verbose_name="講師行銷成本負擔比例(%)")
    company_marketing_share_percent = models.PositiveSmallIntegerField(verbose_name="公司行銷成本負擔比例(%)")

    teacher_amount = models.IntegerField(default=0, verbose_name="講師應付金額")
    company_amount = models.IntegerField(default=0, verbose_name="公司實收金額")

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='confirmed', verbose_name="狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    reversed_at = models.DateTimeField(blank=True, null=True, verbose_name="沖銷時間")

    def recompute(self):
        gross_teacher = round(self.gross_amount * self.teacher_split_percent / 100)
        gross_company = self.gross_amount - gross_teacher
        cost_teacher = round(self.marketing_cost * self.teacher_marketing_share_percent / 100)
        cost_company = self.marketing_cost - cost_teacher
        self.teacher_amount = gross_teacher - cost_teacher
        self.company_amount = gross_company - cost_company

    def save(self, *args, **kwargs):
        self.recompute()
        super().save(*args, **kwargs)

    @classmethod
    def create_for_order_item(cls, item):
        setting = CourseSplitSetting.for_course(item.course)
        record, _ = cls.objects.get_or_create(
            order_item=item,
            defaults={
                'order': item.order,
                'course': item.course,
                'teacher': item.course.teacher,
                'gross_amount': item.paid_amount,
                'teacher_split_percent': setting.teacher_split_percent,
                'company_split_percent': setting.company_split_percent,
                'teacher_marketing_share_percent': setting.teacher_marketing_share_percent,
                'company_marketing_share_percent': setting.company_marketing_share_percent,
            }
        )
        return record

    def __str__(self):
        return f"{self.course.title} - 訂單#{self.order_id} - 講師 NT$ {self.teacher_amount}"

    class Meta:
        verbose_name = "收支分潤紀錄"
        verbose_name_plural = "收支分潤紀錄"

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('completed', '已完成'),
        ('rejected', '已拒絕'),
    ]

    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="withdrawal_requests", verbose_name="講師"
    )
    amount = models.PositiveIntegerField(verbose_name="提領金額")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="狀態"
    )
    note = models.TextField(blank=True, null=True, verbose_name="處理備註")
    bank_info_snapshot = models.TextField(blank=True, default='', verbose_name="銀行帳戶快照")
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="申請時間")
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name="處理時間")

    def clean(self):
        if self.pk is None:
            balance = self.available_balance(self.teacher)
            if self.amount > balance:
                raise ValidationError(f'提領金額超過可提領餘額（NT$ {balance}）')

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def available_balance(cls, teacher):
        confirmed = RevenueRecord.objects.filter(
            teacher=teacher, status='confirmed'
        ).aggregate(total=Sum('teacher_amount'))['total'] or 0
        reserved = cls.objects.filter(
            teacher=teacher, status__in=['pending', 'completed']
        ).aggregate(total=Sum('amount'))['total'] or 0
        return confirmed - reserved

    def __str__(self):
        return f"{self.teacher.username} - NT$ {self.amount} - {self.get_status_display()}"

    class Meta:
        verbose_name = "提領紀錄"
        verbose_name_plural = "提領紀錄"
        ordering = ['-requested_at']

class TeacherFollow(models.Model):
    follower = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="following", verbose_name="追蹤者"
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="followers", verbose_name="講師"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="追蹤時間")

    def __str__(self):
        return f"{self.follower.username} → {self.teacher.username}"

    class Meta:
        verbose_name = "追蹤講師"
        verbose_name_plural = "追蹤講師"
        unique_together = ('follower', 'teacher')
        ordering = ['-created_at']

class TeacherColumn(models.Model):
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="columns", verbose_name="講師"
    )
    title = models.CharField(max_length=200, verbose_name="專欄名稱")
    description = models.TextField(blank=True, default='', verbose_name="專欄簡介")
    cover_image = models.ImageField(
        upload_to='teacher_columns/', blank=True, null=True, verbose_name="專欄封面"
    )
    is_published = models.BooleanField(default=True, verbose_name="是否公開")
    is_paid = models.BooleanField(default=False, verbose_name="付費訂閱專欄")
    monthly_price = models.PositiveIntegerField(default=0, verbose_name="月費（NT$）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.teacher.username} - {self.title}"

    def has_access(self, user):
        if not self.is_paid:
            return True
        if not user.is_authenticated:
            return False
        if user.id == self.teacher_id:
            return True
        return self.subscriptions.filter(
            user=user, expires_at__gte=timezone.now()
        ).exists()

    class Meta:
        verbose_name = "專欄"
        verbose_name_plural = "專欄"
        ordering = ['-created_at']

class TeacherArticle(models.Model):
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="articles", verbose_name="講師"
    )
    column = models.ForeignKey(
        TeacherColumn, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="articles", verbose_name="所屬專欄"
    )
    title = models.CharField(max_length=200, verbose_name="文章標題")
    content = models.TextField(verbose_name="文章內容")
    cover_image = models.ImageField(
        upload_to='teacher_articles/', blank=True, null=True, verbose_name="文章封面"
    )
    is_published = models.BooleanField(default=True, verbose_name="是否公開")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def __str__(self):
        return f"{self.teacher.username} - {self.title}"

    class Meta:
        verbose_name = "文章"
        verbose_name_plural = "文章"
        ordering = ['-created_at']

class TeacherMaterial(models.Model):
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="materials", verbose_name="講師"
    )
    title = models.CharField(max_length=200, verbose_name="教材名稱")
    description = models.TextField(blank=True, default='', verbose_name="教材說明")
    file = models.FileField(upload_to='teacher_materials/', verbose_name="教材檔案")
    is_published = models.BooleanField(default=True, verbose_name="是否公開")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    def __str__(self):
        return f"{self.teacher.username} - {self.title}"

    class Meta:
        verbose_name = "教材"
        verbose_name_plural = "教材"
        ordering = ['-created_at']

class UserBadge(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="badges", verbose_name="使用者"
    )
    code = models.CharField(max_length=50, verbose_name="徽章代碼")
    earned_at = models.DateTimeField(auto_now_add=True, verbose_name="獲得時間")

    def __str__(self):
        return f"{self.user.username} - {self.code}"

    class Meta:
        verbose_name = "成就徽章"
        verbose_name_plural = "成就徽章"
        unique_together = ('user', 'code')
        ordering = ['-earned_at']

class ColumnSubscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="column_subscriptions", verbose_name="訂閱者"
    )
    column = models.ForeignKey(
        'TeacherColumn', on_delete=models.CASCADE, related_name="subscriptions", verbose_name="專欄"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="訂閱開始")
    expires_at = models.DateTimeField(verbose_name="到期時間")

    def is_active(self):
        return self.expires_at >= timezone.now()

    def __str__(self):
        return f"{self.user.username} → {self.column.title}"

    class Meta:
        verbose_name = "專欄訂閱"
        verbose_name_plural = "專欄訂閱"
        ordering = ['-started_at']

class TeacherBankAccount(models.Model):
    teacher = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="bank_account", verbose_name="教師"
    )
    bank_name = models.CharField(max_length=100, verbose_name="銀行名稱")
    bank_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="銀行代碼")
    branch_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="分行名稱")
    account_name = models.CharField(max_length=100, verbose_name="戶名")
    account_number = models.CharField(max_length=50, verbose_name="帳號")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    def is_complete(self):
        return bool(self.bank_name and self.account_name and self.account_number)

    def snapshot_text(self):
        parts = [self.bank_name]
        if self.bank_code:
            parts.append(f'（{self.bank_code}）')
        if self.branch_name:
            parts.append(self.branch_name)
        return f"{''.join(parts)} / 戶名：{self.account_name} / 帳號：{self.account_number}"

    def __str__(self):
        return f"{self.teacher.username} - {self.bank_name} {self.account_number}"

    class Meta:
        verbose_name = "教師銀行帳戶"
        verbose_name_plural = "教師銀行帳戶"

class MarketingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('processing', '處理中'),
        ('completed', '已完成'),
        ('rejected', '已退回'),
    ]

    GOAL_CHOICES = [
        ('exposure', '增加課程曝光'),
        ('enrollment', '增加招生人數'),
        ('new_course', '新課程宣傳'),
        ('promotion', '限時促銷'),
        ('other', '其他'),
    ]

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='marketing_requests',
        verbose_name='教師'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='marketing_requests',
        verbose_name='課程'
    )

    goal = models.CharField(
        max_length=30,
        choices=GOAL_CHOICES,
        verbose_name='行銷目的'
    )

    desired_start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='希望開始日期'
    )

    notes = models.TextField(
        blank=True,
        default='',
        verbose_name='補充需求'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='申請狀態'
    )

    admin_note = models.TextField(
        blank=True,
        default='',
        verbose_name='後台備註'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='申請時間'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新時間'
    )

    def __str__(self):
        return f'{self.course.title} - {self.teacher.username} - {self.get_status_display()}'

    class Meta:
        verbose_name = 'AI 行銷申請'
        verbose_name_plural = 'AI 行銷申請'
        ordering = ['-created_at']

class MarketingPlan(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('reviewing', '待審核'),
        ('approved', '已核准'),
        ('rejected', '已退回'),
    ]

    marketing_request = models.OneToOneField(
        MarketingRequest,
        on_delete=models.CASCADE,
        related_name='plan',
        verbose_name='行銷申請',
    )

    target_audience = models.TextField(
        blank=True,
        default='',
        verbose_name='目標受眾'
    )

    course_selling_points = models.TextField(
        blank=True,
        default='',
        verbose_name='課程賣點'
    )

    marketing_strategy = models.TextField(
        blank=True,
        default='',
        verbose_name='行銷策略'
    )

    ad_headline = models.TextField(
        blank=True,
        default='',
        verbose_name='廣告標題'
    )

    ad_copy = models.TextField(
        blank=True,
        default='',
        verbose_name='廣告文案'
    )

    social_media_copy = models.TextField(
        blank=True,
        default='',
        verbose_name='社群貼文'
    )

    video_script = models.TextField(
        blank=True,
        default='',
        verbose_name='短影音腳本'
    )

    call_to_action = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='行動呼籲'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='企劃狀態'
    )

    admin_note = models.TextField(
        blank=True,
        default='',
        verbose_name='管理員備註'
    )

    generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='AI 生成時間'
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='審核時間'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='建立時間'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新時間'
    )

    def __str__(self):
        return f'{self.marketing_request.course.title} - AI 行銷企劃'

    class Meta:
        verbose_name = 'AI 行銷企劃'
        verbose_name_plural = 'AI 行銷企劃'
        ordering = ['-created_at']

class VMAccessRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已核發'),
        ('rejected', '已拒絕'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='vm_access_requests', verbose_name='申請學生'
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='vm_access_requests', verbose_name='購買課程'
    )
    reason = models.TextField(
        blank=True, default='', verbose_name='申請原因',
        help_text='例如：課程需要的軟體只有 Windows 版本，Mac 無法安裝。'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='申請狀態'
    )

    vm_url = models.CharField(max_length=255, blank=True, default='', verbose_name='虛擬機網址')
    vm_username = models.CharField(max_length=100, blank=True, default='', verbose_name='虛擬機帳號')
    vm_password = models.CharField(max_length=100, blank=True, default='', verbose_name='虛擬機密碼')

    admin_note = models.TextField(blank=True, default='', verbose_name='後台備註')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申請時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='核發時間')

    def is_fulfilled(self):
        return bool(self.vm_url and self.vm_username and self.vm_password)

    def __str__(self):
        return f'{self.student.username} - {self.course.title} - {self.get_status_display()}'

    class Meta:
        verbose_name = 'Mac 虛擬機申請'
        verbose_name_plural = 'Mac 虛擬機申請'
        ordering = ['-created_at']
