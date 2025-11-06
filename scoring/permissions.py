"""
權限控制模組
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定義權限：只有房間的創建者可以修改，其他人只能讀取
    """
    
    def has_object_permission(self, request, view, obj):
        # 讀取權限對所有人開放
        if request.method in permissions.SAFE_METHODS:
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
    """
    
    def has_permission(self, request, view):
        # 讀取操作對所有人開放
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 創建操作需要認證
        if request.method == 'POST':
            return request.user.is_authenticated
        
        # 更新和刪除操作需要認證
        return request.user.is_authenticated

