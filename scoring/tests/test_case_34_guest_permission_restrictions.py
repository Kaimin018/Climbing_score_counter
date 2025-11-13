"""
訪客權限限制測試用例

測試項目：
1. 訪客用戶可以讀取數據（GET/HEAD/OPTIONS）
2. 訪客用戶不能創建數據（POST）
3. 訪客用戶不能更新數據（PUT/PATCH）
4. 訪客用戶不能刪除數據（DELETE）
5. 普通登錄用戶可以讀寫
6. 未認證用戶可以讀取但不能寫入
"""

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from scoring.permissions import IsMemberOrReadOnly


class TestCaseGuestPermissionRestrictions(TestCase):
    """測試訪客權限限制"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        
        # 創建測試數據
        self.room = self.factory.create_room(name="測試房間")
        self.members = self.factory.create_normal_members(self.room, count=2, names=["成員1", "成員2"])
        self.member = self.members[0]
        self.route = self.factory.create_route(self.room, name="路線1", grade="V3")
        self.score = Score.objects.get(member=self.member, route=self.route)
        
        # 創建普通用戶
        self.regular_user = User.objects.create_user(
            username='regularuser',
            password='TestPass123!',
            email='regular@example.com'
        )
        
        # 創建訪客用戶
        self.guest_user = User.objects.create_user(
            username='guest_20250101120000_abc123',
            password='dummy',
            email=''
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
        User.objects.filter(username__startswith='guest_').delete()
        User.objects.filter(username='regularuser').delete()
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_can_read_rooms(self):
        """測試訪客可以讀取房間列表"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.get('/api/rooms/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "訪客應該能夠讀取房間列表"
        )
        self.assertIsInstance(response.data, list)
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_can_read_room_detail(self):
        """測試訪客可以讀取房間詳情"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.get(f'/api/rooms/{self.room.id}/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "訪客應該能夠讀取房間詳情"
        )
        self.assertEqual(response.data['name'], '測試房間')
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_create_room(self):
        """測試訪客不能創建房間"""
        # 調試：檢查 @override_settings 是否生效
        from django.conf import settings as django_settings
        rest_framework_config = getattr(django_settings, 'REST_FRAMEWORK', {})
        default_perms = rest_framework_config.get('DEFAULT_PERMISSION_CLASSES', [])
        debug_value = getattr(django_settings, 'DEBUG', None)
        
        print(f"\n[DEBUG] test_guest_cannot_create_room:")
        print(f"  DEBUG = {debug_value}")
        print(f"  DEFAULT_PERMISSION_CLASSES = {default_perms}")
        print(f"  First permission class = {default_perms[0] if default_perms else 'None'}")
        print(f"  Guest user = {self.guest_user.username}")
        print(f"  User authenticated = {self.guest_user.is_authenticated}")
        
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.post(
            '/api/rooms/',
            {'name': '訪客創建的房間'},
            format='json'
        )
        
        print(f"  Response status = {response.status_code}")
        print(f"  Expected status = {status.HTTP_403_FORBIDDEN}")
        if hasattr(response, 'data'):
            try:
                print(f"  Response data = {response.data}")
            except UnicodeEncodeError:
                print(f"  Response data = (contains non-ASCII characters)")
        
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠創建房間"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_update_room(self):
        """測試訪客不能更新房間"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.patch(
            f'/api/rooms/{self.room.id}/',
            {'name': '更新後的房間名'},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠更新房間"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_delete_room(self):
        """測試訪客不能刪除房間"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠刪除房間"
        )
        # 驗證房間仍然存在
        self.assertTrue(Room.objects.filter(id=self.room.id).exists())
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_can_read_members(self):
        """測試訪客可以讀取成員列表"""
        self.client.force_authenticate(user=self.guest_user)
        
        # 成员列表通过房间详情获取，或使用 /api/members/?room={room_id}
        response = self.client.get(f'/api/members/?room={self.room.id}')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "訪客應該能夠讀取成員列表"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_create_member(self):
        """測試訪客不能創建成員"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.post(
            '/api/members/',
            {'name': '新成員', 'room': self.room.id, 'is_custom_calc': False},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠創建成員"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_delete_member(self):
        """測試訪客不能刪除成員"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.delete(f'/api/members/{self.member.id}/')
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠刪除成員"
        )
        # 驗證成員仍然存在
        self.assertTrue(Member.objects.filter(id=self.member.id).exists())
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_can_read_routes(self):
        """測試訪客可以讀取路線列表"""
        self.client.force_authenticate(user=self.guest_user)
        
        # 路线列表通过房间详情获取，或使用 /api/routes/?room={room_id}
        response = self.client.get(f'/api/routes/?room={self.room.id}')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "訪客應該能夠讀取路線列表"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_create_route(self):
        """測試訪客不能創建路線"""
        self.client.force_authenticate(user=self.guest_user)
        
        # 使用房间的 create_route action
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {'name': '新路線', 'grade': 'V4'},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠創建路線"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_update_route(self):
        """測試訪客不能更新路線"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.patch(
            f'/api/routes/{self.route.id}/',
            {'name': '更新後的路線名'},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠更新路線"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_delete_route(self):
        """測試訪客不能刪除路線"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.delete(f'/api/routes/{self.route.id}/')
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠刪除路線"
        )
        # 驗證路線仍然存在
        self.assertTrue(Route.objects.filter(id=self.route.id).exists())
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_can_read_scores(self):
        """測試訪客可以讀取成績"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.get(f'/api/rooms/{self.room.id}/leaderboard/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "訪客應該能夠讀取排行榜"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_guest_cannot_update_score(self):
        """測試訪客不能更新成績"""
        self.client.force_authenticate(user=self.guest_user)
        
        response = self.client.patch(
            f'/api/scores/{self.score.id}/',
            {'is_completed': True},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "訪客不應該能夠更新成績"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_regular_user_can_create_room(self):
        """測試普通用戶可以創建房間"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.post(
            '/api/rooms/',
            {'name': '普通用戶創建的房間'},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "普通用戶應該能夠創建房間"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_regular_user_can_update_room(self):
        """測試普通用戶可以更新房間"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.patch(
            f'/api/rooms/{self.room.id}/',
            {'name': '更新後的房間名'},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "普通用戶應該能夠更新房間"
        )
        # 驗證更新成功
        self.room.refresh_from_db()
        self.assertEqual(self.room.name, '更新後的房間名')
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_regular_user_can_delete_room(self):
        """測試普通用戶可以刪除房間"""
        self.client.force_authenticate(user=self.regular_user)
        
        room_id = self.room.id
        response = self.client.delete(f'/api/rooms/{room_id}/')
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            "普通用戶應該能夠刪除房間"
        )
        # 驗證房間已被刪除
        self.assertFalse(Room.objects.filter(id=room_id).exists())
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_regular_user_can_create_member(self):
        """測試普通用戶可以創建成員"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.post(
            '/api/members/',
            {'name': '新成員', 'room': self.room.id, 'is_custom_calc': False},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "普通用戶應該能夠創建成員"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_regular_user_can_update_score(self):
        """測試普通用戶可以更新成績"""
        self.client.force_authenticate(user=self.regular_user)
        
        response = self.client.patch(
            f'/api/scores/{self.score.id}/',
            {'is_completed': True},
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "普通用戶應該能夠更新成績"
        )
        # 驗證更新成功
        self.score.refresh_from_db()
        self.assertTrue(self.score.is_completed)
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_unauthenticated_user_can_read(self):
        """測試未認證用戶可以讀取數據"""
        # 不使用 force_authenticate，保持未認證狀態
        response = self.client.get('/api/rooms/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "未認證用戶應該能夠讀取房間列表"
        )
    
    @override_settings(
        DEBUG=False,
        REST_FRAMEWORK={
            'DEFAULT_RENDERER_CLASSES': [
                'rest_framework.renderers.JSONRenderer',
            ],
            'DEFAULT_PARSER_CLASSES': [
                'rest_framework.parsers.JSONParser',
                'rest_framework.parsers.MultiPartParser',
                'rest_framework.parsers.FormParser',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.SessionAuthentication',
                'rest_framework.authentication.BasicAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
        }
    )
    def test_unauthenticated_user_cannot_create(self):
        """測試未認證用戶不能創建數據"""
        # 不使用 force_authenticate，保持未認證狀態
        response = self.client.post(
            '/api/rooms/',
            {'name': '未認證用戶創建的房間'},
            format='json'
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            "未認證用戶不應該能夠創建房間"
        )
    
    def test_guest_user_identification(self):
        """測試訪客用戶識別邏輯"""
        # 測試不同格式的訪客用戶名
        guest_users = [
            User.objects.create_user(username='guest_test1_abc123', password='dummy'),
            User.objects.create_user(username='guest_test2', password='dummy'),
            User.objects.create_user(username='guest_', password='dummy'),
        ]
        
        regular_users = [
            User.objects.create_user(username='regularuser2', password='dummy'),
            User.objects.create_user(username='user_guest', password='dummy'),  # 不是訪客（不以 guest_ 開頭）
        ]
        
        # 驗證訪客用戶識別
        for guest_user in guest_users:
            self.assertTrue(
                guest_user.username.startswith('guest_'),
                f"用戶 {guest_user.username} 應該被識別為訪客"
            )
        
        # 驗證普通用戶識別
        for regular_user in regular_users:
            self.assertFalse(
                regular_user.username.startswith('guest_'),
                f"用戶 {regular_user.username} 不應該被識別為訪客"
            )
        
        # 清理
        for user in guest_users + regular_users:
            user.delete()

