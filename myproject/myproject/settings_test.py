from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

AUTH_PASSWORD_VALIDATORS = []
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
