from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MemberViewSet, RouteViewSet, ScoreViewSet

router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'members', MemberViewSet, basename='member')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'scores', ScoreViewSet, basename='score')

urlpatterns = [
    path('', include(router.urls)),
]

