from .models import Notification, TeacherFollow, Enrollment

def notify_users(user_ids, title, content):
    ids = {uid for uid in user_ids if uid}
    if not ids:
        return 0
    Notification.objects.bulk_create(
        [Notification(user_id=uid, title=title, content=content) for uid in ids]
    )
    return len(ids)

def notify_followers(teacher, title, content):
    ids = TeacherFollow.objects.filter(teacher=teacher).values_list('follower_id', flat=True)
    return notify_users(ids, title, content)

def notify_course_buyers(course, title, content, exclude_user_id=None):
    ids = Enrollment.objects.filter(course=course).values_list('student_id', flat=True)
    ids = [uid for uid in ids if uid != exclude_user_id]
    return notify_users(ids, title, content)
