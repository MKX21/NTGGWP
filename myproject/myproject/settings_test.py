"""測試專用設定：改用本機記憶體 SQLite，完全不碰共用雲端 MySQL。

用法：
    python manage.py test main --settings=myproject.settings_test

為什麼不直接用 settings：共用雲端 MySQL 上跑 test 會嘗試 CREATE DATABASE
test_<name>，那需要額外權限、跨網路跑 migration 很慢，而且測試資料庫名字固定
—— 兩個組員同時跑測試會互相砍掉對方的測試庫。
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 測試不需要密碼強度檢查，也不需要慢的 hasher
AUTH_PASSWORD_VALIDATORS = []
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
