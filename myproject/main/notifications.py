"""站內通知的集中發送工具。

所有「一次發給多人」的通知都走這裡，統一用 bulk_create 一次寫入，
避免在各 view 各自迴圈 Notification.objects.create() 造成 N 次查詢。
"""
from .models import Notification, TeacherFollow, Enrollment


def notify_users(user_ids, title, content):
    """對一批 user id 發送相同通知；回傳實際發送數。"""
    ids = {uid for uid in user_ids if uid}
    if not ids:
        return 0
    Notification.objects.bulk_create(
        [Notification(user_id=uid, title=title, content=content) for uid in ids]
    )
    return len(ids)


def notify_followers(teacher, title, content):
    """通知某講師的所有追蹤者。"""
    ids = TeacherFollow.objects.filter(teacher=teacher).values_list('follower_id', flat=True)
    return notify_users(ids, title, content)


def notify_course_buyers(course, title, content, exclude_user_id=None):
    """通知已購買（已開通）某課程的所有學員。"""
    ids = Enrollment.objects.filter(course=course).values_list('student_id', flat=True)
    ids = [uid for uid in ids if uid != exclude_user_id]
    return notify_users(ids, title, content)
