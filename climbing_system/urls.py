"""
URL configuration for climbing_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from scoring.views import index_view, leaderboard_view, rules_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index_view, name='index'),
    path('leaderboard/<int:room_id>/', leaderboard_view, name='leaderboard'),
    path('rules/', rules_view, name='rules'),
    path('api/', include('scoring.urls')),
]

# 開發環境下提供媒體文件服務
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

