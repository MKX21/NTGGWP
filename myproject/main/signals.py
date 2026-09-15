from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Profile

@receiver(user_logged_in)
def ensure_profile_exists(sender, request, user, **kwargs):
    Profile.objects.get_or_create(
        user=user, defaults={'role': 'student', 'is_teacher': False}
    )
