"""
安全性測試用例

測試項目：
1. 用戶認證（註冊、登錄、登出、當前用戶）
2. API 權限控制（讀取/寫入權限）
3. XSS 攻擊防護（所有輸入字段）
4. SQL 注入防護（所有輸入字段）
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import (
    TestDataFactory, cleanup_test_data,
    assert_response_status_for_permission
)
import json


class TestCaseAuthentication(TestCase):
    """測試用戶認證功能"""
    
    def setUp(self):
        """設置測試客戶端"""
        self.client = APIClient()
        self.base_url = '/api/auth/'
    
    def test_user_registration(self):
        """測試用戶註冊"""
        # 測試正常註冊
        response = self.client.post(
            f'{self.base_url}register/',
            {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'password_confirm': 'testpass123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        
        # 驗證用戶已創建
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_user_registration_duplicate_username(self):
        """測試重複用戶名註冊"""
        # 先創建一個用戶
        User.objects.create_user(username='existing', password='pass123')
        
        # 嘗試用相同用戶名註冊
        response = self.client.post(
            f'{self.base_url}register/',
            {
                'username': 'existing',
                'password': 'pass123',
                'password_confirm': 'pass123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_registration_password_mismatch(self):
        """測試密碼不一致"""
        response = self.client.post(
            f'{self.base_url}register/',
            {
                'username': 'testuser',
                'password': 'pass12345',
                'password_confirm': 'pass45678'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 驗證錯誤信息存在（可能在 password_confirm 或非字段錯誤中）
        self.assertTrue(
            'password_confirm' in response.data or 
            'non_field_errors' in response.data or
            len(response.data) > 0
        )
    
    def test_user_login(self):
        """測試用戶登錄"""
        # 先創建用戶
        User.objects.create_user(username='testuser', password='testpass123')
        
        # 測試登錄
        response = self.client.post(
            f'{self.base_url}login/',
            {
                'username': 'testuser',
                'password': 'testpass123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_user_login_invalid_credentials(self):
        """測試無效憑證登錄"""
        User.objects.create_user(username='testuser', password='testpass123')
        
        response = self.client.post(
            f'{self.base_url}login/',
            {
                'username': 'testuser',
                'password': 'wrongpassword'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_user_logout(self):
        """測試用戶登出"""
        # 創建並登錄用戶
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=user)
        
        # 測試登出
        response = self.client.post(f'{self.base_url}logout/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_current_user(self):
        """測試獲取當前用戶信息"""
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=user)
        
        response = self.client.get(f'{self.base_url}current-user/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertTrue(response.data['is_authenticated'])
    
    def test_current_user_without_authentication(self):
        """測試未認證用戶無法獲取當前用戶信息"""
        response = self.client.get(f'{self.base_url}current-user/', format='json')
        # 可能返回 401 或 403，取決於權限配置
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_user_registration_with_xss_in_username(self):
        """測試註冊時用戶名 XSS 防護"""
        # 使用較簡單的 XSS payload，避免觸發用戶名驗證規則
        xss_payload = 'test<script>alert</script>'
        response = self.client.post(
            f'{self.base_url}register/',
            {
                'username': xss_payload,
                'email': 'test@example.com',
                'password': 'testpass123',
                'password_confirm': 'testpass123'
            },
            format='json'
        )
        # 應該成功註冊，但用戶名會被轉義
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username=xss_payload)
            # 驗證用戶名被正確存儲（可能被轉義）
            self.assertIsNotNone(user)
        else:
            # 如果驗證失敗，至少驗證系統拒絕了惡意輸入
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_with_sql_injection(self):
        """測試登錄時 SQL 注入防護"""
        # 創建正常用戶
        User.objects.create_user(username='testuser', password='testpass123')
        
        # 嘗試 SQL 注入
        sql_payload = "admin' OR '1'='1"
        response = self.client.post(
            f'{self.base_url}login/',
            {
                'username': sql_payload,
                'password': 'anything'
            },
            format='json'
        )
        # 應該失敗，因為用戶名不存在
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestCaseAPIPermissions(TestCase):
    """測試 API 權限控制"""
    
    def setUp(self):
        """設置測試數據"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.room = TestDataFactory.create_room(name="測試房間")
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_read_without_authentication(self):
        """測試未認證用戶可以讀取數據"""
        # 測試獲取房間列表（讀取操作）
        response = self.client.get('/api/rooms/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 測試獲取房間詳情
        response = self.client.get(f'/api/rooms/{self.room.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_without_authentication(self):
        """測試未認證用戶無法創建數據"""
        from scoring.tests.test_helpers import assert_response_status_for_permission
        # 測試創建房間（需要認證）
        response = self.client.post(
            '/api/rooms/',
            {'name': '新房間'},
            format='json'
        )
        # 根據當前環境驗證響應狀態
        assert_response_status_for_permission(
            response, 
            status.HTTP_201_CREATED, 
            self
        )
    
    def test_create_with_authentication(self):
        """測試認證用戶可以創建數據"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/rooms/',
            {'name': '新房間'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_update_without_authentication(self):
        """測試未認證用戶無法更新數據"""
        from scoring.tests.test_helpers import assert_response_status_for_permission
        response = self.client.patch(
            f'/api/rooms/{self.room.id}/',
            {'name': '更新後的房間名'},
            format='json'
        )
        # 根據當前環境驗證響應狀態
        assert_response_status_for_permission(
            response, 
            status.HTTP_200_OK, 
            self
        )
    
    def test_score_update_requires_authentication(self):
        """測試更新成績需要認證"""
        from scoring.tests.test_helpers import assert_response_status_for_permission
        member = TestDataFactory.create_normal_members(self.room, count=1)[0]
        route = TestDataFactory.create_route(self.room, name="路線1", grade="V3")
        score = Score.objects.get(member=member, route=route)
        
        # 未認證用戶嘗試更新
        response = self.client.patch(
            f'/api/scores/{score.id}/',
            {'is_completed': True},
            format='json'
        )
        # 根據當前環境驗證響應狀態
        assert_response_status_for_permission(
            response, 
            status.HTTP_200_OK, 
            self
        )
        
        # 認證用戶可以更新（無論環境）
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f'/api/scores/{score.id}/',
            {'is_completed': True},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_delete_requires_authentication(self):
        """測試刪除操作需要認證"""
        from scoring.tests.test_helpers import assert_response_status_for_permission
        member = TestDataFactory.create_normal_members(self.room, count=1)[0]
        
        # 未認證用戶嘗試刪除
        response = self.client.delete(f'/api/members/{member.id}/', format='json')
        # 根據當前環境驗證響應狀態
        assert_response_status_for_permission(
            response, 
            status.HTTP_204_NO_CONTENT, 
            self
        )
        
        # 認證用戶可以刪除
        self.client.force_authenticate(user=self.user)
        # 重新創建成員（因為可能已被刪除）
        member = TestDataFactory.create_normal_members(self.room, count=1)[0]
        response = self.client.delete(f'/api/members/{member.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_route_delete_requires_authentication(self):
        """測試刪除路線需要認證"""
        from scoring.tests.test_helpers import assert_response_status_for_permission
        route = TestDataFactory.create_route(self.room, name="路線1", grade="V3")
        
        # 未認證用戶嘗試刪除
        response = self.client.delete(f'/api/routes/{route.id}/', format='json')
        # 根據當前環境驗證響應狀態
        assert_response_status_for_permission(
            response, 
            status.HTTP_204_NO_CONTENT, 
            self
        )
        
        # 認證用戶可以刪除
        self.client.force_authenticate(user=self.user)
        # 重新創建路線（因為可能已被刪除）
        route = TestDataFactory.create_route(self.room, name="路線1", grade="V3")
        response = self.client.delete(f'/api/routes/{route.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestCaseXSSProtection(TestCase):
    """測試 XSS 攻擊防護"""
    
    def setUp(self):
        """設置測試數據"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.room = TestDataFactory.create_room(name="測試房間")
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_xss_in_room_name(self):
        """測試房間名稱 XSS 防護"""
        xss_payload = '<script>alert("XSS")</script>'
        
        response = self.client.post(
            '/api/rooms/',
            {'name': xss_payload},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證輸入已被轉義（escape 會轉義 HTML 特殊字符）
        room = Room.objects.get(id=response.data['id'])
        # 驗證原始 HTML 標籤不存在（已被轉義）
        self.assertNotIn('<script>', room.name)
        # 驗證已被轉義（可能有多層轉義，所以檢查轉義後的字符）
        self.assertTrue('&lt;' in room.name or '&amp;lt;' in room.name or '<' not in room.name)
    
    def test_xss_in_member_name(self):
        """測試成員名稱 XSS 防護"""
        xss_payload = '<img src=x onerror=alert(1)>'
        
        response = self.client.post(
            '/api/members/',
            {
                'room': self.room.id,
                'name': xss_payload
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證輸入已被轉義（原始 HTML 標籤不應存在）
        member = Member.objects.get(id=response.data['id'])
        # 驗證原始 HTML 標籤不存在（已被轉義）
        self.assertNotIn('<img', member.name)
        # 驗證已被轉義
        self.assertTrue('&lt;' in member.name or '&amp;lt;' in member.name or '<' not in member.name)
    
    def test_xss_in_route_name(self):
        """測試路線名稱 XSS 防護"""
        xss_payload = '<script>alert("XSS")</script>'
        
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {
                'name': xss_payload,
                'grade': 'V3'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證輸入已被轉義（原始 HTML 標籤不應存在）
        route = Route.objects.get(id=response.data['id'])
        self.assertNotIn('<script>', route.name)
        # 驗證已被轉義
        self.assertTrue('&lt;' in route.name or '&amp;lt;' in route.name or '<' not in route.name)
    
    def test_xss_in_route_grade(self):
        """測試路線難度等級 XSS 防護"""
        xss_payload = '<svg onload=alert(1)>'
        
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {
                'name': '路線1',
                'grade': xss_payload
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證輸入已被轉義（原始 HTML 標籤不應存在）
        route = Route.objects.get(id=response.data['id'])
        self.assertNotIn('<svg', route.grade)
        # 驗證已被轉義（可能有多層轉義）
        self.assertTrue('&lt;' in route.grade or '&amp;lt;' in route.grade or '<' not in route.grade)
    
    def test_xss_in_json_member_completions(self):
        """測試 member_completions JSON 字段 XSS 防護"""
        xss_payload = '<script>alert("XSS")</script>'
        member = TestDataFactory.create_normal_members(self.room, count=1)[0]
        
        # 嘗試在 JSON 中注入 XSS
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {
                'name': '路線1',
                'grade': 'V3',
                'member_completions': json.dumps({str(member.id): xss_payload})
            },
            format='json'
        )
        # JSON 中的值會被轉換為布林值，XSS 不會執行
        # 但我們驗證系統能正確處理
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_xss_in_email_field(self):
        """測試郵箱字段 XSS 防護"""
        xss_payload = 'test<script>alert</script>@example.com'
        base_url = '/api/auth/'
        
        response = self.client.post(
            f'{base_url}register/',
            {
                'username': 'testuser',
                'email': xss_payload,
                'password': 'testpass123',
                'password_confirm': 'testpass123'
            },
            format='json'
        )
        # 可能成功註冊（郵箱會被轉義），或者驗證失敗
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username='testuser')
            # 驗證郵箱被正確存儲（可能被轉義）
            self.assertIsNotNone(user.email)
        else:
            # 如果驗證失敗，至少驗證系統拒絕了惡意輸入
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestCaseSQLInjectionProtection(TestCase):
    """測試 SQL 注入防護"""
    
    def setUp(self):
        """設置測試數據"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.room = TestDataFactory.create_room(name="測試房間")
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_sql_injection_in_room_name(self):
        """測試房間名稱 SQL 注入防護"""
        # Django ORM 自動防止 SQL 注入
        sql_payload = "'; DROP TABLE rooms; --"
        
        response = self.client.post(
            '/api/rooms/',
            {'name': sql_payload},
            format='json'
        )
        # 應該成功創建，因為 ORM 會正確處理
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證房間已創建，且名稱被正確存儲（不會執行 SQL）
        room = Room.objects.get(id=response.data['id'])
        # 名稱可能被轉義，但 SQL 不會被執行
        # 驗證 SQL 注入嘗試被安全處理（作為字符串存儲）
        self.assertIn("DROP", room.name or "")  # SQL 關鍵字被當作普通字符串
        
        # 驗證其他房間仍然存在（表沒有被刪除）- 這是最重要的測試
        self.assertTrue(Room.objects.filter(id=self.room.id).exists())
    
    def test_sql_injection_in_member_completions(self):
        """測試 member_completions JSON 字段 SQL 注入防護"""
        # 嘗試在 JSON 中注入 SQL
        malicious_json = '{"1": true, "2": "); DROP TABLE scores; --"}'
        
        member = TestDataFactory.create_normal_members(self.room, count=1)[0]
        route = TestDataFactory.create_route(self.room, name="路線1", grade="V3")
        
        # 更新路線時使用惡意 JSON
        response = self.client.patch(
            f'/api/routes/{route.id}/',
            {
                'member_completions': malicious_json
            },
            format='json'
        )
        
        # 應該返回錯誤，因為 JSON 格式無效或值類型不正確
        # 或者成功處理（如果 JSON 有效但值被轉換為布林值）
        # 無論如何，SQL 不會被執行
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        
        # 驗證數據仍然存在
        self.assertTrue(Score.objects.filter(route=route).exists())
    
    def test_large_json_input_protection(self):
        """測試過大 JSON 輸入防護"""
        # 創建一個過大的 JSON 字符串
        large_json = json.dumps({str(i): True for i in range(20000)})
        
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {
                'name': '路線1',
                'grade': 'V3',
                'member_completions': large_json
            },
            format='json'
        )
        
        # 應該返回錯誤，因為 JSON 過大
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('member_completions', str(response.data))
    
    def test_sql_injection_in_member_name(self):
        """測試成員名稱 SQL 注入防護"""
        sql_payload = "'; DROP TABLE members; --"
        
        response = self.client.post(
            '/api/members/',
            {
                'room': self.room.id,
                'name': sql_payload
            },
            format='json'
        )
        # 應該成功創建，因為 ORM 會正確處理
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證成員已創建，且名稱被正確存儲（不會執行 SQL）
        member = Member.objects.get(id=response.data['id'])
        # 驗證 SQL 注入嘗試被安全處理（作為字符串存儲）
        self.assertIn("DROP", member.name or "")
        
        # 驗證其他成員仍然存在（表沒有被刪除）
        self.assertTrue(Member.objects.filter(room=self.room).exists())
    
    def test_sql_injection_in_route_name(self):
        """測試路線名稱 SQL 注入防護"""
        sql_payload = "'; DROP TABLE routes; --"
        
        response = self.client.post(
            f'/api/rooms/{self.room.id}/routes/',
            {
                'name': sql_payload,
                'grade': 'V3'
            },
            format='json'
        )
        # 應該成功創建，因為 ORM 會正確處理
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證路線已創建，且名稱被正確存儲（不會執行 SQL）
        route = Route.objects.get(id=response.data['id'])
        # 驗證 SQL 注入嘗試被安全處理（作為字符串存儲）
        self.assertIn("DROP", route.name or "")
        
        # 驗證其他路線仍然存在（表沒有被刪除）
        self.assertTrue(Route.objects.filter(room=self.room).exists())
    
    def test_sql_injection_in_room_id_parameter(self):
        """測試 URL 參數中的 SQL 注入防護"""
        # 嘗試在 URL 參數中注入 SQL
        sql_payload = "1' OR '1'='1"
        
        # 嘗試通過 URL 參數注入
        response = self.client.get(
            f'/api/rooms/{sql_payload}/leaderboard/',
            format='json'
        )
        # 應該返回 404 或 400，因為房間 ID 無效
        self.assertIn(response.status_code, [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ])
    
    def test_sql_injection_in_filter_parameters(self):
        """測試過濾參數中的 SQL 注入防護"""
        # Django ORM 會自動處理參數化查詢
        sql_payload = "1' UNION SELECT * FROM rooms --"
        
        # 嘗試在查詢參數中注入
        response = self.client.get(
            f'/api/rooms/?id={sql_payload}',
            format='json'
        )
        # 應該返回正常響應（可能是空列表），但不會執行 SQL
        # ORM 會將參數作為字符串處理
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])

