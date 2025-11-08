"""
測試輔助工具模組

提供常用的測試序列函數，方便測試案例快速創建測試數據
"""
from django.conf import settings
from rest_framework import status
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score, update_scores


class TestDataFactory:
    """測試數據工廠類，提供常見的測試數據創建序列"""
    
    @staticmethod
    def create_room(name="測試房間", standard_line_score=None):
        """
        創建測試房間
        
        Args:
            name: 房間名稱
            standard_line_score: 每一條線總分（如果不提供，會自動計算）
        
        Returns:
            Room: 創建的房間對象
        """
        if standard_line_score is not None:
            return Room.objects.create(name=name, standard_line_score=standard_line_score)
        else:
            return Room.objects.create(name=name)
    
    @staticmethod
    def create_normal_members(room, count=2, names=None):
        """
        創建一般組成員
        
        Args:
            room: Room 對象
            count: 成員數量
            names: 成員名稱列表（如果提供，則使用提供的名稱，否則使用默認名稱）
        
        Returns:
            list: 創建的成員對象列表
        """
        members = []
        default_names = [f"成員{i+1}" for i in range(count)]
        member_names = names if names else default_names
        
        for i, name in enumerate(member_names[:count]):
            member = Member.objects.create(
                room=room,
                name=name,
                is_custom_calc=False
            )
            members.append(member)
        
        return members
    
    @staticmethod
    def create_custom_members(room, count=1, names=None):
        """
        創建客製化組成員
        
        Args:
            room: Room 對象
            count: 成員數量
            names: 成員名稱列表（如果提供，則使用提供的名稱，否則使用默認名稱）
        
        Returns:
            list: 創建的成員對象列表
        """
        members = []
        default_names = [f"客製化成員{i+1}" for i in range(count)]
        member_names = names if names else default_names
        
        for i, name in enumerate(member_names[:count]):
            member = Member.objects.create(
                room=room,
                name=name,
                is_custom_calc=True
            )
            members.append(member)
        
        return members
    
    @staticmethod
    def create_route(room, name="路線1", grade="V3", members=None, member_completions=None):
        """
        創建測試路線並自動創建成績記錄
        
        Args:
            room: Room 對象
            name: 路線名稱
            grade: 難度等級
            members: 成員列表（如果不提供，會使用房間內的所有成員）
            member_completions: 成員完成狀態字典 {member_id: is_completed}
                              如果提供，會設置對應的完成狀態
                              如果不提供，所有成員預設為未完成
        
        Returns:
            Route: 創建的路線對象
        """
        route = Route.objects.create(room=room, name=name, grade=grade)
        
        # 如果沒有提供成員列表，使用房間內的所有成員
        if members is None:
            members = Member.objects.filter(room=room)
        
        # 創建成績記錄
        for member in members:
            is_completed = False
            if member_completions and member.id in member_completions:
                is_completed = member_completions[member.id]
            elif member_completions and str(member.id) in member_completions:
                is_completed = member_completions[str(member.id)]
            
            Score.objects.create(
                member=member,
                route=route,
                is_completed=is_completed
            )
        
        return route
    
    @staticmethod
    def create_route_with_scores(room, name="路線1", grade="V3", 
                                  scores_config=None):
        """
        創建測試路線並根據配置創建成績記錄
        
        Args:
            room: Room 對象
            name: 路線名稱
            grade: 難度等級
            scores_config: 成績配置列表，格式：
                [
                    {'member': member_obj, 'is_completed': True},
                    {'member': member_obj, 'is_completed': False},
                ]
                如果提供，會按配置創建成績記錄
                如果不提供，會為所有成員創建未完成的成績記錄
        
        Returns:
            Route: 創建的路線對象
        """
        route = Route.objects.create(room=room, name=name, grade=grade)
        
        if scores_config:
            for score_config in scores_config:
                Score.objects.create(
                    member=score_config['member'],
                    route=route,
                    is_completed=score_config.get('is_completed', False)
                )
        else:
            # 如果沒有提供配置，為所有成員創建未完成的成績記錄
            members = Member.objects.filter(room=room)
            for member in members:
                Score.objects.create(
                    member=member,
                    route=route,
                    is_completed=False
                )
        
        return route


def cleanup_test_photos(room=None, routes=None):
    """
    清理測試中創建的圖片文件
    
    Args:
        room: Room 對象或房間 ID，如果提供會清理該房間所有路線的圖片
        routes: Route 對象列表或單個 Route 對象，如果提供會清理指定路線的圖片
    """
    routes_to_clean = []
    
    if room:
        if isinstance(room, Room):
            room_id = room.id
        else:
            room_id = room
        routes_to_clean.extend(Route.objects.filter(room_id=room_id))
    
    if routes:
        if isinstance(routes, Route):
            routes_to_clean.append(routes)
        elif isinstance(routes, list):
            for route in routes:
                if isinstance(route, Route):
                    routes_to_clean.append(route)
                elif isinstance(route, int):
                    route_obj = Route.objects.filter(id=route).first()
                    if route_obj:
                        routes_to_clean.append(route_obj)
    
    # 清理圖片文件
    for route in routes_to_clean:
        if route.photo and default_storage.exists(route.photo.name):
            try:
                default_storage.delete(route.photo.name)
            except Exception:
                # 如果刪除失敗，忽略錯誤（可能是文件已經被刪除）
                pass


def cleanup_test_data(room=None, routes=None, cleanup_photos=False):
    """
    清理測試數據
    
    Args:
        room: Room 對象或房間 ID，如果提供會刪除整個房間（包括所有相關的路線、成員、成績）
        routes: Route 對象列表或單個 Route 對象，如果提供會刪除指定的路線
        cleanup_photos: 是否同時清理測試中創建的圖片文件（默認 False）
    """
    # 如果需要清理圖片，在刪除數據前先清理
    if cleanup_photos:
        cleanup_test_photos(room=room, routes=routes)
    
    if room:
        if isinstance(room, Room):
            room_id = room.id
        else:
            room_id = room
        Room.objects.filter(id=room_id).delete()
    
    if routes:
        if isinstance(routes, Route):
            routes.delete()
        elif isinstance(routes, list):
            for route in routes:
                if isinstance(route, Route):
                    route.delete()
                elif isinstance(route, int):
                    Route.objects.filter(id=route).delete()


def create_basic_test_setup(room_name="測試房間", 
                             normal_member_count=2,
                             custom_member_count=0,
                             member_names=None):
    """
    創建基本的測試設置：房間 + 成員
    
    Args:
        room_name: 房間名稱
        normal_member_count: 一般組成員數量
        custom_member_count: 客製化組成員數量
        member_names: 成員名稱字典 {'normal': [...], 'custom': [...]}
    
    Returns:
        dict: {
            'room': Room 對象,
            'normal_members': 一般組成員列表,
            'custom_members': 客製化組成員列表,
            'all_members': 所有成員列表
        }
    """
    room = TestDataFactory.create_room(name=room_name)
    
    normal_names = None
    custom_names = None
    if member_names:
        normal_names = member_names.get('normal')
        custom_names = member_names.get('custom')
    
    normal_members = TestDataFactory.create_normal_members(
        room, 
        count=normal_member_count,
        names=normal_names
    )
    
    custom_members = []
    if custom_member_count > 0:
        custom_members = TestDataFactory.create_custom_members(
            room,
            count=custom_member_count,
            names=custom_names
        )
    
    return {
        'room': room,
        'normal_members': normal_members,
        'custom_members': custom_members,
        'all_members': normal_members + custom_members
    }


def is_allow_any_permission():
    """
    檢查當前環境是否使用 AllowAny 權限
    
    Returns:
        bool: 如果使用 AllowAny 返回 True，否則返回 False
    """
    default_perms = settings.REST_FRAMEWORK.get('DEFAULT_PERMISSION_CLASSES', [])
    return 'AllowAny' in str(default_perms)


def is_debug_mode():
    """
    檢查當前是否為開發模式
    
    Returns:
        bool: 如果 DEBUG=True 返回 True，否則返回 False
    """
    return settings.DEBUG


def should_allow_unauthenticated_access():
    """
    檢查當前環境是否應該允許未認證訪問
    
    在開發環境（DEBUG=True）或使用 AllowAny 時，允許未認證訪問
    
    Returns:
        bool: 如果應該允許未認證訪問返回 True，否則返回 False
    """
    return is_allow_any_permission() or is_debug_mode()


def assert_response_status_for_permission(response, expected_success_status, test_case):
    """
    根據當前權限配置驗證響應狀態碼
    
    Args:
        response: API 響應對象
        expected_success_status: 成功時期望的狀態碼（如 status.HTTP_201_CREATED）
        test_case: TestCase 實例，用於調用斷言方法
    
    Returns:
        None: 直接進行斷言，不返回值
    """
    if should_allow_unauthenticated_access():
        # 開發環境允許訪問，應該成功
        test_case.assertEqual(response.status_code, expected_success_status)
    else:
        # 生產環境需要認證，應該被拒絕
        test_case.assertIn(
            response.status_code, 
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )


def get_logging_handlers():
    """
    獲取當前日誌配置的 handlers
    
    Returns:
        dict: 日誌 handlers 字典
    """
    return settings.LOGGING.get('handlers', {})


def has_file_logging():
    """
    檢查當前是否配置了文件日誌
    
    Returns:
        bool: 如果配置了 file handler 返回 True，否則返回 False
    """
    handlers = get_logging_handlers()
    return 'file' in handlers

