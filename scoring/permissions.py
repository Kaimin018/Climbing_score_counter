"""
權限控制模組
"""
from rest_framework import permissions
from django.conf import settings


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定義權限：只有房間的創建者可以修改，其他人只能讀取
    """
    
    def has_object_permission(self, request, view, obj):
        # 讀取權限對所有人開放
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 開發環境允許所有操作
        if settings.DEBUG:
            return True
        
        # 寫入權限需要認證
        if not request.user.is_authenticated:
            return False
        
        # 檢查是否是房間的創建者（如果對象有 created_by 字段）
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # 對於 Room 對象，檢查是否是創建者
        if hasattr(obj, 'room') and hasattr(obj.room, 'created_by'):
            return obj.room.created_by == request.user
        
        # 默認允許認證用戶
        return True


class IsAuthenticatedOrReadOnlyForCreate(permissions.BasePermission):
    """
    自定義權限：創建操作需要認證，其他操作允許讀取
    開發環境（DEBUG=True）允許所有操作
    """
    
    def has_permission(self, request, view):
        # 開發環境允許所有操作（用於測試）
        if settings.DEBUG:
            return True
        
        # 讀取操作對所有人開放
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 創建操作需要認證
        if request.method == 'POST':
            return request.user.is_authenticated
        
        # 更新和刪除操作需要認證
        return request.user.is_authenticated


class IsMemberOrReadOnly(permissions.BasePermission):
    """
    權限控制：區分訪客和普通成員
    - 訪客用戶（username 以 'guest_' 開頭）：只能讀取（GET/HEAD/OPTIONS）
    - 普通登錄用戶：可以讀寫
    - 未認證用戶：只能讀取
    - 開發環境（DEBUG=True）：允許所有操作（便於測試）
    """
    
    def has_permission(self, request, view):
        # 開發環境允許所有操作（用於測試）
        if settings.DEBUG:
            return True
        
        # 讀取操作對所有人開放
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 寫入操作需要認證
        if not request.user.is_authenticated:
            return False
        
        # 檢查是否是訪客用戶（用戶名以 'guest_' 開頭）
        if request.user.username.startswith('guest_'):
            return False  # 訪客不能進行寫入操作
        
        # 普通登錄用戶可以進行寫入操作
        return True
