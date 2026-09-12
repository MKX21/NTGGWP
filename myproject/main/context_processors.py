"""全站共用的模板 context（導覽列購物車數量、未讀通知數、角色、分類）。"""
from .models import CartItem, Notification, Profile, CourseCategory


def nav_context(request):
    data = {
        'nav_cart_count': 0,
        'nav_unread_count': 0,
        'nav_role': None,
        'nav_avatar_url': None,
        'nav_categories': CourseCategory.objects.order_by('name')[:8],
    }
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        data['nav_cart_count'] = CartItem.objects.filter(cart__user=user).count()
        data['nav_unread_count'] = Notification.objects.filter(user=user, is_read=False).count()
        try:
            profile = user.profile
            data['nav_role'] = profile.role
            if profile.avatar:
                data['nav_avatar_url'] = profile.avatar.url
        except Profile.DoesNotExist:
            data['nav_role'] = None
    return data
