from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import Enrollment, LearningRecord, UserBadge

BADGES = [
    ('first_course', '初次啟程', '購買第一門課程', '🚀', 'courses', 1),
    ('collector', '藏書家', '購買 5 門課程', '📚', 'courses', 5),
    ('warmup', '學習新星', '累積觀看 60 分鐘', '⭐', 'minutes', 60),
    ('devoted', '求知若渴', '累積觀看 600 分鐘', '🔥', 'minutes', 600),
    ('streak3', '三日之約', '連續學習 3 天', '🌱', 'streak', 3),
    ('streak7', '七日精進', '連續學習 7 天', '💪', 'streak', 7),
    ('streak30', '堅持不懈', '連續學習 30 天', '🏆', 'streak', 30),
]

BADGE_MAP = {b[0]: b for b in BADGES}

def _learning_dates(user):
    dts = LearningRecord.objects.filter(user=user).values_list('watched_at', flat=True)
    return {timezone.localtime(dt).date() for dt in dts}

def current_streak(user):
    dates = _learning_dates(user)
    if not dates:
        return 0
    today = timezone.localdate()
    if today in dates:
        cursor = today
    elif (today - timedelta(days=1)) in dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

def longest_streak(user):
    dates = sorted(_learning_dates(user))
    if not dates:
        return 0
    best = run = 1
    for prev, cur in zip(dates, dates[1:]):
        if (cur - prev).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best

def _stats(user):
    courses = Enrollment.objects.filter(student=user).count()
    minutes = LearningRecord.objects.filter(user=user).aggregate(t=Sum('minutes'))['t'] or 0
    streak = max(current_streak(user), longest_streak(user))
    return {'courses': courses, 'minutes': minutes, 'streak': streak}

def evaluate_badges(user):
    stats = _stats(user)
    earned = set(UserBadge.objects.filter(user=user).values_list('code', flat=True))
    newly = []
    for code, name, desc, icon, kind, threshold in BADGES:
        if code in earned:
            continue
        if stats.get(kind, 0) >= threshold:
            UserBadge.objects.get_or_create(user=user, code=code)
            newly.append(code)
    return newly

def badge_progress(user):
    stats = _stats(user)
    earned = set(UserBadge.objects.filter(user=user).values_list('code', flat=True))
    result = []
    for code, name, desc, icon, kind, threshold in BADGES:
        have = stats.get(kind, 0)
        result.append({
            'code': code, 'name': name, 'desc': desc, 'icon': icon,
            'earned': code in earned,
            'current': min(have, threshold), 'threshold': threshold,
            'percent': min(100, round(have / threshold * 100)) if threshold else 100,
        })
    return result
