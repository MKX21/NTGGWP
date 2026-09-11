"""登入保險：使用者登入時若沒有 Profile 就自動補一筆（預設學生）。

避免以非一般註冊流程建立的帳號（createsuperuser、後台手動建立、舊資料）
因為缺 Profile 而在 profile_view / my_courses 等頁面被導回首頁。
"""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Profile


@receiver(user_logged_in)
def ensure_profile_exists(sender, request, user, **kwargs):
    Profile.objects.get_or_create(
        user=user, defaults={'role': 'student', 'is_teacher': False}
    )
