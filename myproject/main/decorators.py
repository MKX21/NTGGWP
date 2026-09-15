"""
View decorators：角色檢查。

取代 views.py 裡 25 處重複的 try/except Profile.DoesNotExist + role 判斷，
統一成 @require_teacher / @require_student / @require_superuser 三個 decorator，
每個都自帶 @login_required，不需要額外疊加。
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Profile


def require_teacher(view_func):
    """限教師（role=='teacher' 或 is_teacher）才能存取的 view。

    自帶 @login_required，未登入自動導向登入頁，
    已登入但不是教師導向首頁。
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.profile
            if profile.role == 'teacher' or profile.is_teacher:
                return view_func(request, *args, **kwargs)
        except Profile.DoesNotExist:
            pass
        return redirect('home')
    return wrapper


def require_student(view_func):
    """限學生（role=='student'）才能存取的 view。

    自帶 @login_required。
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            profile = request.user.profile
            if profile.role == 'student':
                return view_func(request, *args, **kwargs)
        except Profile.DoesNotExist:
            pass
        return redirect('home')
    return wrapper


def require_superuser(view_func):
    """限管理員（is_superuser）才能存取的 view。

    自帶 @login_required。
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper
