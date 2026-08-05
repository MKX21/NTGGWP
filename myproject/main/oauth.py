"""Google / LINE 快速登入（OAuth 2.0）用的授權網址組合與 code 交換工具。"""
import re
import secrets

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Profile

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

LINE_AUTH_URL = 'https://access.line.me/oauth2/v2.1/authorize'
LINE_TOKEN_URL = 'https://api.line.me/oauth2/v2.1/token'
LINE_VERIFY_URL = 'https://api.line.me/oauth2/v2.1/verify'

OAUTH_TIMEOUT = 10  # 秒


class OAuthError(Exception):
    """交換 code 或取得使用者資料失敗時拋出，callback view 會導回登入頁並顯示錯誤。"""


def new_state():
    return secrets.token_urlsafe(24)


def _callback_uri(request, view_name):
    return request.build_absolute_uri(reverse(view_name))


def build_google_auth_url(request, state):
    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': _callback_uri(request, 'google_oauth_callback'),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    }
    query = '&'.join(f'{k}={requests.utils.quote(str(v))}' for k, v in params.items())
    return f'{GOOGLE_AUTH_URL}?{query}'


def fetch_google_profile(request, code):
    """用 authorization code 換 access token，再取得 sub/email/name。回傳 (provider_id, email, name)。"""
    token_resp = requests.post(GOOGLE_TOKEN_URL, data={
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'code': code,
        'redirect_uri': _callback_uri(request, 'google_oauth_callback'),
        'grant_type': 'authorization_code',
    }, timeout=OAUTH_TIMEOUT)
    if not token_resp.ok:
        raise OAuthError(f'Google token 交換失敗：{token_resp.text}')

    access_token = token_resp.json().get('access_token')
    if not access_token:
        raise OAuthError('Google 未回傳 access_token')

    info_resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=OAUTH_TIMEOUT,
    )
    if not info_resp.ok:
        raise OAuthError(f'Google 使用者資料取得失敗：{info_resp.text}')

    info = info_resp.json()
    provider_id = info.get('sub')
    if not provider_id:
        raise OAuthError('Google 回傳資料缺少 sub')

    return provider_id, info.get('email') or '', info.get('name') or ''


def build_line_auth_url(request, state):
    params = {
        'response_type': 'code',
        'client_id': settings.LINE_LOGIN_CHANNEL_ID,
        'redirect_uri': _callback_uri(request, 'line_oauth_callback'),
        'state': state,
        'scope': 'profile openid email',
    }
    query = '&'.join(f'{k}={requests.utils.quote(str(v))}' for k, v in params.items())
    return f'{LINE_AUTH_URL}?{query}'


def fetch_line_profile(request, code):
    """用 code 換 token，並透過 LINE 的 verify 端點解出 id_token 內的 sub/email/name。"""
    token_resp = requests.post(LINE_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': _callback_uri(request, 'line_oauth_callback'),
        'client_id': settings.LINE_LOGIN_CHANNEL_ID,
        'client_secret': settings.LINE_LOGIN_CHANNEL_SECRET,
    }, timeout=OAUTH_TIMEOUT)
    if not token_resp.ok:
        raise OAuthError(f'LINE token 交換失敗：{token_resp.text}')

    id_token = token_resp.json().get('id_token')
    if not id_token:
        raise OAuthError('LINE 未回傳 id_token')

    verify_resp = requests.post(LINE_VERIFY_URL, data={
        'id_token': id_token,
        'client_id': settings.LINE_LOGIN_CHANNEL_ID,
    }, timeout=OAUTH_TIMEOUT)
    if not verify_resp.ok:
        raise OAuthError(f'LINE id_token 驗證失敗：{verify_resp.text}')

    claims = verify_resp.json()
    provider_id = claims.get('sub')
    if not provider_id:
        raise OAuthError('LINE 回傳資料缺少 sub')

    return provider_id, claims.get('email') or '', claims.get('name') or ''


def _unique_username(base):
    base = re.sub(r'[^\w.@+-]', '', base) or 'user'
    base = base[:120]
    username = base
    suffix = 0
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'
    return username


def get_or_create_user(provider, provider_id, email, display_name):
    """依 provider_id 找回帳號；找不到再用 email 綁定既有帳號；都沒有就建立新的學生帳號。"""
    field = f'{provider}_id'

    profile = Profile.objects.filter(**{field: provider_id}).select_related('user').first()
    if profile:
        return profile.user

    if email:
        user = User.objects.filter(email=email).first()
        if user:
            profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
            setattr(profile, field, provider_id)
            profile.save(update_fields=[field])
            return user

    username = _unique_username(email.split('@')[0] if email else f'{provider}_{provider_id}')
    user = User.objects.create_user(username=username, email=email)
    user.set_unusable_password()
    if display_name:
        user.first_name = display_name[:150]
        user.save(update_fields=['first_name', 'password'])
    else:
        user.save(update_fields=['password'])

    Profile.objects.create(user=user, role='student', **{field: provider_id})
    return user
