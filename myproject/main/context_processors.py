from .models import CartItem, Enrollment, Notification, Profile, CourseCategory

def nav_context(request):
    data = {
        'nav_cart_count': 0,
        'nav_unread_count': 0,
        'nav_role': None,
        'nav_can_teach': False,
        'nav_avatar_url': None,
        'nav_categories': CourseCategory.objects.order_by('name')[:8],
        'nav_enrolled_ids': set(),
    }
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        data['nav_cart_count'] = CartItem.objects.filter(cart__user=user).count()
        data['nav_unread_count'] = Notification.objects.filter(user=user, is_read=False).count()
        data['nav_enrolled_ids'] = set(
            Enrollment.objects.filter(student=user).values_list('course_id', flat=True)
        )
        try:
            profile = user.profile
            data['nav_role'] = profile.role
            data['nav_can_teach'] = profile.role == 'teacher' or profile.is_teacher
            if profile.avatar:
                data['nav_avatar_url'] = profile.avatar.url
        except Profile.DoesNotExist:
            data['nav_role'] = None
    return data
