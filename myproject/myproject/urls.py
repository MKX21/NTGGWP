from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings

from main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]

if settings.DEBUG:
    # 支援 Range 請求的媒體服務（影片可正常播放/拖曳）
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', main_views.serve_media),
    ]