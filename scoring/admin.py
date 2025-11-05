from django.contrib import admin
from .models import Room, Member, Route, Score


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'standard_line_score', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'room', 'is_custom_calc', 'total_score', 'completed_routes_count']
    list_filter = ['is_custom_calc', 'room']
    search_fields = ['name']
    raw_id_fields = ['room']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade', 'room', 'created_at']
    list_filter = ['room', 'created_at']
    search_fields = ['name', 'grade']
    raw_id_fields = ['room']


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ['member', 'route', 'is_completed', 'score_attained']
    list_filter = ['is_completed', 'route__room']
    search_fields = ['member__name', 'route__name']
    raw_id_fields = ['member', 'route']






