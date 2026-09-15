from django import forms
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from .models import (
    Course,
    CourseCategory,
    Review,
    CourseChapter,
    CourseLesson,
    LessonMaterial,
    CourseQuestion,
    CourseAnswer,
    CourseAnnouncement,
    CourseComment,
    Profile,
    TeacherColumn,
    TeacherArticle,
    TeacherMaterial,
    TeacherBankAccount,
    MarketingRequest,
    VMAccessRequest,
)

class ListTextWidget(forms.TextInput):
    def __init__(self, data_list, list_id, attrs=None):
        super().__init__(attrs)
        self._list = data_list
        self._list_id = list_id
        self.attrs.update({'list': list_id, 'autocomplete': 'off'})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super().render(name, value, attrs=attrs, renderer=renderer)
        options = ''.join('<option value="%s">' % item for item in self._list)
        datalist = '<datalist id="%s">%s</datalist>' % (self._list_id, options)
        return mark_safe(text_html + datalist)

class CourseForm(forms.ModelForm):
    category_name = forms.CharField(
        label='課程分類',
        max_length=100,
        help_text='可點選現有分類，或直接輸入新分類（自動建立）',
    )

    field_order = [
        'title', 'category_name', 'level', 'description', 'image',
        'intro_video_file', 'intro_video_url',
        'price', 'discount_price',
        'is_crowdfunding', 'funding_goal', 'funding_start_date', 'funding_end_date', 'early_bird_price',
    ]

    class Meta:
        model = Course
        fields = [
            'title', 'level', 'price', 'description', 'image',
            'intro_video_file', 'intro_video_url',
            'discount_price',
            'is_crowdfunding', 'funding_goal', 'funding_start_date', 'funding_end_date', 'early_bird_price',
        ]
        labels = {
            'title': '課程名稱',
            'level': '課程難度',
            'price': '原價',
            'description': '課程介紹',
            'image': '課程封面圖',
            'intro_video_file': '課程封面介紹影片（上傳 mp4，學員可於課程頁放大觀看）',
            'intro_video_url': '或貼介紹影片連結',
            'discount_price': '折扣價（選填）',
            'is_crowdfunding': '這是一門募資課程',
            'funding_goal': '募資門檻人數',
            'funding_start_date': '募資開始時間',
            'funding_end_date': '募資結束時間',
            'early_bird_price': '早鳥優惠價（募資期間適用）',
        }
        help_texts = {
            'discount_price': '設定後，課程將顯示原價刪除線與折扣價。',
            'funding_goal': '達到此人數即視為募資成功。',
            'early_bird_price': '募資期間內購買者適用此價格，需低於原價。',
        }
        widgets = {
            'funding_start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'funding_end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'intro_video_file': forms.ClearableFileInput(attrs={'accept': 'video/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['funding_start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['funding_end_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['funding_goal'].required = False
        self.fields['funding_start_date'].required = False
        self.fields['funding_end_date'].required = False
        self.fields['early_bird_price'].required = False
        self.fields['discount_price'].required = False

        names = list(
            CourseCategory.objects.order_by('name').values_list('name', flat=True)
        )
        self.fields['category_name'].widget = ListTextWidget(
            data_list=names,
            list_id='category_options',
            attrs={'placeholder': '選擇或輸入分類名稱'}
        )
        if self.instance and self.instance.pk and self.instance.category:
            self.fields['category_name'].initial = self.instance.category.name

    def clean_category_name(self):
        name = (self.cleaned_data.get('category_name') or '').strip()
        if not name:
            raise forms.ValidationError('請選擇或輸入課程分類。')
        return name

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        discount_price = cleaned.get('discount_price')
        is_crowdfunding = cleaned.get('is_crowdfunding')
        funding_goal = cleaned.get('funding_goal')
        funding_start = cleaned.get('funding_start_date')
        funding_end = cleaned.get('funding_end_date')
        early_bird_price = cleaned.get('early_bird_price')

        if discount_price and price and discount_price >= price:
            self.add_error('discount_price', '折扣價必須低於原價。')

        if is_crowdfunding:
            if not funding_goal:
                self.add_error('funding_goal', '募資課程請設定門檻人數（大於 0）。')
            if not funding_start or not funding_end:
                self.add_error('funding_end_date', '募資課程請設定募資起訖時間。')
            elif funding_end <= funding_start:
                self.add_error('funding_end_date', '募資結束時間必須晚於開始時間。')
            if early_bird_price and price and early_bird_price >= price:
                self.add_error('early_bird_price', '早鳥優惠價必須低於原價。')

        return cleaned

    def save(self, commit=True):
        course = super().save(commit=False)
        category, _ = CourseCategory.objects.get_or_create(
            name=self.cleaned_data['category_name']
        )
        course.category = category
        if commit:
            course.save()
        return course

class ChapterForm(forms.ModelForm):
    class Meta:
        model = CourseChapter
        fields = ['title', 'description', 'sort_order']
        labels = {
            'title': '章節名稱',
            'description': '章節說明',
            'sort_order': '章節順序',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = CourseLesson
        fields = ['title', 'content', 'video_file', 'video_url', 'sort_order', 'is_free_preview']
        labels = {
            'title': '單元名稱',
            'content': '單元內容',
            'video_file': '上傳影片檔（mp4，時長自動偵測）',
            'video_url': '或貼影片連結',
            'sort_order': '單元順序',
            'is_free_preview': '免費試看',
        }
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'video_file': forms.ClearableFileInput(attrs={'accept': 'video/*'}),
        }

class LessonMaterialForm(forms.ModelForm):
    class Meta:
        model = LessonMaterial
        fields = ['title', 'material_type', 'file', 'sort_order']
        labels = {
            'title': '教材名稱（例：第 1 節簡報、練習範例）',
            'material_type': '教材類型',
            'file': '檔案（pptx / docx / pdf / 圖片等）',
            'sort_order': '排序',
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = CourseQuestion
        fields = ['content']
        labels = {'content': '問題內容'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': '請描述你的問題'}),
        }

class AnswerForm(forms.ModelForm):
    class Meta:
        model = CourseAnswer
        fields = ['content']
        labels = {'content': '回答內容'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': '輸入你的回答'}),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = CourseAnnouncement
        fields = ['title', 'content']
        labels = {'title': '公告標題', 'content': '公告內容'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': '輸入要通知學員的公告內容'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = CourseComment
        fields = ['content']
        labels = {'content': '留言內容'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': '留下你的想法或心得'}),
        }

class RegisterForm(forms.Form):
    username = forms.CharField(label='帳號', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'username'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    password = forms.CharField(label='密碼', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirm_password = forms.CharField(label='確認密碼', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('這個帳號已經被使用了。')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('兩次輸入的密碼不一致。')

        return cleaned_data

class CouponApplyForm(forms.Form):
    coupon_code = forms.CharField(
        label='優惠碼',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '請輸入優惠碼，沒有可留空'
        })
    )

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']

        labels = {
            'rating': '評分',
            'comment': '評論內容',
        }

        widgets = {
            'rating': forms.Select(
                choices=[
                    (5, '5 星 - 非常滿意'),
                    (4, '4 星 - 滿意'),
                    (3, '3 星 - 普通'),
                    (2, '2 星 - 不太滿意'),
                    (1, '1 星 - 不滿意'),
                ]
            ),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': '請輸入你對這門課的想法'
            }),
        }

class ProfileEditForm(forms.ModelForm):
    username = forms.CharField(
        label='帳號名稱', max_length=150,
        help_text='用於登入與顯示，不可與其他帳號重複。',
    )
    first_name = forms.CharField(label='名字', max_length=150, required=False)
    last_name = forms.CharField(label='姓氏', max_length=150, required=False)
    email = forms.EmailField(label='Email')

    field_order = [
        'username', 'first_name', 'last_name', 'email',
        'avatar', 'cover_image', 'headline', 'bio', 'facebook_url', 'youtube_url',
    ]

    class Meta:
        model = Profile
        fields = ['avatar', 'cover_image', 'headline', 'bio', 'facebook_url', 'youtube_url']
        labels = {
            'avatar': '大頭貼',
            'cover_image': '講師頁封面',
            'headline': '講師稱號',
            'bio': '講師簡介',
            'facebook_url': 'Facebook 連結',
            'youtube_url': 'YouTube 連結',
        }
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'cover_image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'headline': forms.TextInput(attrs={'placeholder': '一句話介紹你的定位'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': '介紹你的教學背景與專長'}),
            'facebook_url': forms.URLInput(attrs={'placeholder': 'https://facebook.com/...'}),
            'youtube_url': forms.URLInput(attrs={'placeholder': 'https://youtube.com/...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['username'].initial = self.user.username
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('請輸入帳號名稱。')
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('這個帳號名稱已經被使用。')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('這個 Email 已經被其他帳號使用。')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.username = self.cleaned_data['username']
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        if commit:
            self.user.save()
            profile.save()
        return profile

class ColumnForm(forms.ModelForm):
    class Meta:
        model = TeacherColumn
        fields = ['title', 'description', 'cover_image', 'is_published', 'is_paid', 'monthly_price']
        labels = {
            'title': '專欄名稱',
            'description': '專欄簡介',
            'cover_image': '專欄封面',
            'is_published': '公開顯示',
            'is_paid': '設為付費訂閱專欄',
            'monthly_price': '月費（NT$，付費專欄才需填）',
        }
        help_texts = {
            'monthly_price': '訂閱者付費後可閱讀本專欄所有文章，未訂閱者只能看到預覽。',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': '這個專欄在談什麼？'}),
            'cover_image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_paid') and not cleaned.get('monthly_price'):
            self.add_error('monthly_price', '付費專欄請設定月費（大於 0）。')
        return cleaned

class ArticleForm(forms.ModelForm):
    class Meta:
        model = TeacherArticle
        fields = ['title', 'column', 'content', 'cover_image', 'is_published']
        labels = {
            'title': '文章標題',
            'column': '所屬專欄（選填）',
            'content': '文章內容',
            'cover_image': '文章封面',
            'is_published': '公開顯示',
        }
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10, 'placeholder': '開始撰寫你的內容…'}),
            'cover_image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields['column'].queryset = TeacherColumn.objects.filter(teacher=teacher)
        self.fields['column'].required = False

class TeacherBankAccountForm(forms.ModelForm):
    class Meta:
        model = TeacherBankAccount
        fields = ['bank_name', 'bank_code', 'branch_name', 'account_name', 'account_number']
        labels = {
            'bank_name': '銀行名稱',
            'bank_code': '銀行代碼（選填）',
            'branch_name': '分行名稱（選填）',
            'account_name': '戶名',
            'account_number': '帳號',
        }

class MaterialForm(forms.ModelForm):
    class Meta:
        model = TeacherMaterial
        fields = ['title', 'description', 'file', 'is_published']
        labels = {
            'title': '教材名稱',
            'description': '教材說明',
            'file': '教材檔案',
            'is_published': '公開顯示',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': '這份教材的用途與內容'}),
        }

class MarketingRequestForm(forms.ModelForm):
    class Meta:
        model = MarketingRequest
        fields = ['course', 'goal', 'desired_start_date', 'notes']
        labels = {
            'course': '申請課程',
            'goal': '行銷目的',
            'desired_start_date': '希望開始日期',
            'notes': '補充需求',
        }
        help_texts = {
            'notes': '可以簡單告訴後台希望強調的方向，不需要自行撰寫廣告內容。',
        }
        widgets = {
            'desired_start_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 5, 'placeholder': '例如：希望主要推廣給上班族。'}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields['course'].queryset = Course.objects.filter(teacher=teacher).order_by('-created_at')

class VMAccessRequestForm(forms.ModelForm):
    class Meta:
        model = VMAccessRequest
        fields = ['course', 'reason']
        labels = {
            'course': '哪一門課程需要用到虛擬機',
            'reason': '申請原因（選填）',
        }
        help_texts = {
            'reason': '例如：課程需要的軟體只有 Windows 版本，Mac 無法安裝。',
        }
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': '簡單說明你的使用情境，方便我們核發。'}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['course'].queryset = Course.objects.filter(
                enrollment__student=student
            ).distinct().order_by('-created_at')
