from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MemberViewSet, RouteViewSet, ScoreViewSet
from .auth_views import register_view, login_view, logout_view, current_user_view, guest_login_view

router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'members', MemberViewSet, basename='member')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'scores', ScoreViewSet, basename='score')

urlpatterns = [
    path('', include(router.urls)),
    # 認證相關路由
    path('auth/register/', register_view, name='register'),
    path('auth/login/', login_view, name='login'),
    path('auth/guest-login/', guest_login_view, name='guest-login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/current-user/', current_user_view, name='current-user'),
]

