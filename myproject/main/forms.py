from django import forms
from django.contrib.auth.models import User
from .models import (
    Course,
    CourseCategory,
    Review,
    CourseChapter,
    CourseLesson,
    CourseQuestion,
    CourseAnswer,
    Profile,
    TeacherBankAccount,
)
class CourseForm(forms.ModelForm):
    field_order = [
        'title', 'category', 'level', 'description', 'image',
        'price', 'discount_price',
        'is_crowdfunding', 'funding_goal', 'funding_start_date', 'funding_end_date', 'early_bird_price',
        'promo_video_type',
    ]

    class Meta:
        model = Course
        fields = [
            'title', 'category', 'level', 'price', 'description', 'image',
            'discount_price',
            'is_crowdfunding', 'funding_goal', 'funding_start_date', 'funding_end_date', 'early_bird_price',
            'promo_video_type',
        ]
        labels = {
            'title': '課程名稱',
            'category': '課程分類',
            'level': '課程難度',
            'price': '原價',
            'description': '課程介紹',
            'image': '課程封面',
            'discount_price': '折扣價（選填）',
            'is_crowdfunding': '這是一門募資課程',
            'funding_goal': '募資門檻人數',
            'funding_start_date': '募資開始時間',
            'funding_end_date': '募資結束時間',
            'early_bird_price': '早鳥優惠價（募資期間適用）',
            'promo_video_type': '宣傳影片意向',
        }
        help_texts = {
            'discount_price': '設定後，課程將顯示原價刪除線與折扣價。',
            'funding_goal': '達到此人數即視為募資成功。',
            'early_bird_price': '募資期間內購買者適用此價格，需低於原價。',
            'promo_video_type': '告訴行政人員你希望的宣傳影片拍攝方式，後續會由行政人員安排。',
        }
        widgets = {
            'funding_start_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'funding_end_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
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

        # 分類改為固定清單挑選（由管理員在後台維護），教師不可自訂新分類
        self.fields['category'].queryset = CourseCategory.objects.order_by('name')
        self.fields['category'].required = True
        self.fields['category'].empty_label = '請選擇課程分類'

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
        # duration_minutes 不再由老師手動填，改成上傳影片後自動偵測
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


class QuestionForm(forms.ModelForm):
    class Meta:
        model = CourseQuestion
        fields = ['title', 'content']
        labels = {'title': '問題標題', 'content': '問題內容'}
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


class RegisterForm(forms.Form):
    username = forms.CharField(label='帳號', max_length=150)
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='密碼', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='確認密碼', widget=forms.PasswordInput)

    ROLE_CHOICES = [
        ('student', '學生'),
        ('teacher', '老師'),
    ]

    role = forms.ChoiceField(label='身分', choices=ROLE_CHOICES)

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
    first_name = forms.CharField(label='名字', max_length=150, required=False)
    last_name = forms.CharField(label='姓氏', max_length=150, required=False)
    email = forms.EmailField(label='Email')

    class Meta:
        model = Profile
        fields = ['avatar']
        labels = {'avatar': '大頭貼'}
        widgets = {'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'})}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('這個 Email 已經被其他帳號使用。')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        if commit:
            self.user.save()
            profile.save()
        return profile


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


class WithdrawalRequestForm(forms.Form):
    amount = forms.IntegerField(label='提領金額', min_value=1)

    def __init__(self, *args, available_balance=0, min_amount=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_balance = available_balance
        self.min_amount = min_amount
        self.fields['amount'].widget.attrs.update({'placeholder': f'最低 NT$ {min_amount}'})

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < self.min_amount:
            raise forms.ValidationError(f'單次提領金額不得低於 NT$ {self.min_amount}。')
        if amount > self.available_balance:
            raise forms.ValidationError('提領金額不得超過目前可提領餘額。')
        return amount
