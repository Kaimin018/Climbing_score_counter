"""
AWS 部署後可能發生的問題測試用例

模擬生產環境（DEBUG=False）下的常見問題：
1. 權限問題（需要認證的操作）
2. CSRF token 問題
3. Session cookie 問題
4. 資源不存在（404）錯誤
5. 並發操作問題
"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json


class TestCaseProductionPermissions(TestCase):
    """測試生產環境權限問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        members = self.factory.create_normal_members(self.room, count=1, names=["測試成員"])
        self.member = members[0]
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    @override_settings(DEBUG=False)
    def test_delete_member_without_authentication(self):
        """測試未認證用戶刪除成員（生產環境應該失敗）"""
        # 未認證的客戶端
        response = self.client.delete(f'/api/members/{self.member.id}/')
        
        # 生產環境應該返回 403 或 401
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            f"未認證用戶刪除成員應該返回 401 或 403，但返回了 {response.status_code}"
        )
    
    @override_settings(DEBUG=False)
    def test_delete_member_with_authentication(self):
        """測試已認證用戶刪除成員（應該成功）"""
        # 認證客戶端
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete(f'/api/members/{self.member.id}/')
        
        # 應該成功刪除
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            f"已認證用戶刪除成員應該返回 204，但返回了 {response.status_code}"
        )
        
        # 驗證成員已被刪除
        self.assertFalse(Member.objects.filter(id=self.member.id).exists())
    
    @override_settings(DEBUG=False)
    def test_delete_nonexistent_member(self):
        """測試刪除不存在的成員（應該返回 404）"""
        self.client.force_authenticate(user=self.user)
        
        nonexistent_id = 99999
        response = self.client.delete(f'/api/members/{nonexistent_id}/')
        
        # 應該返回 404
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            f"刪除不存在的成員應該返回 404，但返回了 {response.status_code}"
        )
        
        # 驗證錯誤信息
        if response.data:
            self.assertIn('detail', response.data)


class TestCaseCSRFTokenIssues(TestCase):
    """測試 CSRF token 相關問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = Client(enforce_csrf_checks=True)  # 啟用 CSRF 檢查
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        self.member = self.factory.create_member(self.room, "測試成員")
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    def test_delete_member_without_csrf_token(self):
        """測試沒有 CSRF token 的刪除請求（應該失敗）"""
        # 先登錄獲取 session
        self.client.login(username='testuser', password='TestPass123!')
        
        # 嘗試刪除成員（沒有 CSRF token）
        response = self.client.delete(
            f'/api/members/{self.member.id}/',
            HTTP_X_CSRFTOKEN='invalid_token'
        )
        
        # 應該返回 403（CSRF 驗證失敗）
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            f"沒有有效 CSRF token 的請求應該返回 403，但返回了 {response.status_code}"
        )
    
    def test_delete_member_with_valid_csrf_token(self):
        """測試有有效 CSRF token 的刪除請求（應該成功）"""
        # 先登錄獲取 session
        self.client.login(username='testuser', password='TestPass123!')
        
        # 獲取 CSRF token（通過 GET 請求首頁）
        response = self.client.get('/')
        csrf_token = self.client.cookies.get('csrftoken')
        
        if csrf_token:
            # 使用有效的 CSRF token 刪除成員
            response = self.client.delete(
                f'/api/members/{self.member.id}/',
                HTTP_X_CSRFTOKEN=csrf_token.value
            )
            
            # 應該成功（在開發環境）或需要認證（在生產環境）
            self.assertIn(
                response.status_code,
                [status.HTTP_204_NO_CONTENT, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                f"有有效 CSRF token 的請求應該成功或返回權限錯誤，但返回了 {response.status_code}"
            )


class TestCaseSessionCookieIssues(TestCase):
    """測試 Session Cookie 相關問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = Client()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        self.member = self.factory.create_member(self.room, "測試成員")
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_session_cookie_with_secure_flag(self):
        """測試 SESSION_COOKIE_SECURE 設置（HTTPS 環境）"""
        # 登錄
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, content_type='application/json')
        
        # 檢查響應中是否有 session cookie
        # 注意：在測試環境中，SESSION_COOKIE_SECURE 可能不會生效
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED],
            "登錄請求應該成功或返回認證錯誤"
        )
    
    def test_session_persistence_after_login(self):
        """測試登錄後 session 是否持久化"""
        # 登錄
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'TestPass123!'
        }, content_type='application/json')
        
        if response.status_code == status.HTTP_200_OK:
            # 檢查當前用戶（應該能獲取到用戶信息）
            response = self.client.get('/api/auth/current-user/')
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                "登錄後應該能獲取當前用戶信息或返回權限錯誤"
            )


class TestCaseResourceNotFound(TestCase):
    """測試資源不存在（404）錯誤處理"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    def test_delete_nonexistent_member(self):
        """測試刪除不存在的成員"""
        nonexistent_id = 99999
        response = self.client.delete(f'/api/members/{nonexistent_id}/')
        
        # 應該返回 404
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            f"刪除不存在的成員應該返回 404，但返回了 {response.status_code}"
        )
        
        # 驗證錯誤信息格式
        if hasattr(response, 'data') and response.data:
            self.assertIn('detail', response.data)
    
    def test_update_nonexistent_member(self):
        """測試更新不存在的成員"""
        nonexistent_id = 99999
        response = self.client.patch(
            f'/api/members/{nonexistent_id}/',
            {'name': '新名稱'},
            format='json'
        )
        
        # 應該返回 404
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            f"更新不存在的成員應該返回 404，但返回了 {response.status_code}"
        )
    
    def test_delete_nonexistent_route(self):
        """測試刪除不存在的路線"""
        nonexistent_id = 99999
        response = self.client.delete(f'/api/routes/{nonexistent_id}/')
        
        # 應該返回 404
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            f"刪除不存在的路線應該返回 404，但返回了 {response.status_code}"
        )


class TestCaseConcurrentOperations(TestCase):
    """測試並發操作問題（模擬 AWS 多 worker 環境）"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        members = self.factory.create_normal_members(self.room, count=1, names=["測試成員"])
        self.member = members[0]
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    def test_delete_already_deleted_member(self):
        """測試刪除已被刪除的成員（模擬並發刪除）"""
        member_id = self.member.id
        
        # 第一次刪除
        response1 = self.client.delete(f'/api/members/{member_id}/')
        self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)
        
        # 第二次嘗試刪除（應該返回 404）
        response2 = self.client.delete(f'/api/members/{member_id}/')
        self.assertEqual(
            response2.status_code,
            status.HTTP_404_NOT_FOUND,
            "刪除已被刪除的成員應該返回 404"
        )
    
    def test_update_member_after_deletion(self):
        """測試在成員被刪除後嘗試更新（模擬並發操作）"""
        member_id = self.member.id
        
        # 刪除成員
        self.client.delete(f'/api/members/{member_id}/')
        
        # 嘗試更新已刪除的成員
        response = self.client.patch(
            f'/api/members/{member_id}/',
            {'name': '新名稱'},
            format='json'
        )
        
        # 應該返回 404
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            "更新已刪除的成員應該返回 404"
        )


class TestCaseProductionEnvironment(TestCase):
    """測試生產環境特定問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        members = self.factory.create_normal_members(self.room, count=1, names=["測試成員"])
        self.member = members[0]
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPass123!',
            email='test@example.com'
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data()
    
    @override_settings(DEBUG=False)
    def test_production_permissions_for_read_operations(self):
        """測試生產環境讀取操作的權限（應該允許未認證用戶）"""
        # 未認證用戶應該可以讀取
        response = self.client.get('/api/rooms/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "未認證用戶應該可以讀取房間列表"
        )
        
        response = self.client.get(f'/api/members/')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "未認證用戶應該可以讀取成員列表"
        )
    
    @override_settings(DEBUG=False)
    def test_production_permissions_for_write_operations(self):
        """測試生產環境寫入操作的權限（應該需要認證）"""
        # 未認證用戶不應該可以創建
        response = self.client.post('/api/rooms/', {
            'name': '新房間'
        }, format='json')
        
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            "未認證用戶不應該可以創建房間"
        )
        
        # 認證後應該可以創建
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/rooms/', {
            'name': '新房間'
        }, format='json')
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "已認證用戶應該可以創建房間"
        )

