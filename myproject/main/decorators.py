from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Profile

def require_teacher(view_func):
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
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper
