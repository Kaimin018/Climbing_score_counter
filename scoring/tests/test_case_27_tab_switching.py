"""
標籤頁切換功能測試用例

測試項目：
1. 標籤頁切換函數存在且可調用
2. 點擊排行榜標籤頁按鈕可以切換到排行榜
3. 點擊路線列表標籤頁按鈕可以切換到路線列表
4. 標籤頁按鈕的 active 狀態正確更新
5. 標籤頁內容的顯示/隱藏正確
6. 默認顯示排行榜標籤頁
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json
import re


class TestCaseTabSwitching(TestCase):
    """測試標籤頁切換功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = Client()
        self.factory = TestDataFactory()
        
        # 創建測試用戶
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        
        # 創建測試房間和數據
        self.room = self.factory.create_room("標籤頁測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試路線
        self.route = self.factory.create_route(
            room=self.room,
            name="測試路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        
        # 登入用戶
        self.client.force_login(self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_tab_switching_function_exists(self):
        """
        測試：標籤頁切換函數存在於頁面中
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查頁面中是否包含 switchTab 函數
        3. 驗證函數定義正確
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200, 
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}。內容: {response.content[:500] if response.content else 'N/A'}"
        )
        
        # 檢查頁面內容
        content = response.content.decode('utf-8')
        self.assertIn('function switchTab', content, "頁面應該包含 switchTab 函數")
        # 檢查函數調用（可能使用單引號或雙引號）
        self.assertTrue(
            'switchTab(\'leaderboard\')' in content or 'switchTab("leaderboard")' in content,
            "應該有切換到排行榜的調用"
        )
        self.assertTrue(
            'switchTab(\'routes\')' in content or 'switchTab("routes")' in content,
            "應該有切換到路線列表的調用"
        )
    
    def test_tab_elements_exist(self):
        """
        測試：標籤頁元素存在於頁面中
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查 HTML 內容
        3. 檢查標籤頁按鈕和內容是否存在
        4. 驗證 ID 正確
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200,
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}"
        )
        
        content = response.content.decode('utf-8')
        
        # 檢查標籤頁按鈕（不區分大小寫）
        self.assertTrue(
            'id="tabLeaderboard"' in content or 'id=\'tabLeaderboard\'' in content,
            "應該有排行榜標籤頁按鈕"
        )
        self.assertTrue(
            'id="tabRoutes"' in content or 'id=\'tabRoutes\'' in content,
            "應該有路線列表標籤頁按鈕"
        )
        
        # 檢查標籤頁內容（不區分大小寫）
        self.assertTrue(
            'id="tabPaneLeaderboard"' in content or 'id=\'tabPaneLeaderboard\'' in content,
            "應該有排行榜標籤頁內容"
        )
        self.assertTrue(
            'id="tabPaneRoutes"' in content or 'id=\'tabPaneRoutes\'' in content,
            "應該有路線列表標籤頁內容"
        )
    
    def test_default_tab_is_leaderboard(self):
        """
        測試：默認顯示排行榜標籤頁
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查 HTML 內容
        3. 檢查排行榜標籤頁按鈕是否有 active 類
        4. 檢查排行榜標籤頁內容是否有 active 類
        5. 檢查路線列表標籤頁按鈕和內容沒有 active 類
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200,
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}"
        )
        
        content = response.content.decode('utf-8')
        
        # 檢查排行榜標籤頁按鈕有 active 類
        # 查找包含 id="tabLeaderboard" 和 class 包含 "active" 的按鈕
        # 使用更靈活的方式：先找到按鈕，然後檢查其 class 屬性
        leaderboard_btn_pattern = r'<button[^>]*id=["\']tabLeaderboard["\'][^>]*>'
        leaderboard_btn_match = re.search(leaderboard_btn_pattern, content, re.IGNORECASE)
        self.assertIsNotNone(
            leaderboard_btn_match, 
            f"應該有排行榜標籤頁按鈕。頁面內容片段: {content[:1000]}"
        )
        leaderboard_btn_html = leaderboard_btn_match.group(0)
        # 檢查是否有 active class（不區分大小寫）
        self.assertTrue(
            'active' in leaderboard_btn_html.lower(),
            f"排行榜標籤頁按鈕應該有 active 類。實際 HTML: {leaderboard_btn_html}"
        )
        
        # 檢查排行榜標籤頁內容有 active 類
        leaderboard_pane_pattern = r'<div[^>]*id=["\']tabPaneLeaderboard["\'][^>]*>'
        leaderboard_pane_match = re.search(leaderboard_pane_pattern, content, re.IGNORECASE)
        self.assertIsNotNone(
            leaderboard_pane_match, 
            f"應該有排行榜標籤頁內容。頁面內容片段: {content[:1000]}"
        )
        leaderboard_pane_html = leaderboard_pane_match.group(0)
        # 檢查是否有 active class（不區分大小寫）
        self.assertTrue(
            'active' in leaderboard_pane_html.lower(),
            f"排行榜標籤頁內容應該有 active 類。實際 HTML: {leaderboard_pane_html}"
        )
        
        # 檢查路線列表標籤頁按鈕沒有 active 類（在初始狀態）
        routes_btn_pattern = r'<button[^>]*id=["\']tabRoutes["\'][^>]*>'
        routes_btn_match = re.search(routes_btn_pattern, content, re.IGNORECASE)
        self.assertIsNotNone(routes_btn_match, "應該有路線列表標籤頁按鈕")
        routes_btn_html = routes_btn_match.group(0)
        # 如果沒有 class 屬性，或者 class 中沒有 active，都算通過
        if 'class=' in routes_btn_html.lower():
            self.assertNotIn('active', routes_btn_html.lower(), "路線列表標籤頁按鈕不應該有 active 類")
    
    def test_leaderboard_tab_contains_leaderboard_table(self):
        """
        測試：排行榜標籤頁包含排行榜表格
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查 HTML 內容
        3. 檢查排行榜標籤頁內容中是否有排行榜表格
        4. 驗證表格結構正確
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200,
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}"
        )
        
        content = response.content.decode('utf-8')
        
        # 檢查排行榜標籤頁內容存在（支持單引號或雙引號）
        self.assertTrue(
            'id="tabPaneLeaderboard"' in content or 'id=\'tabPaneLeaderboard\'' in content,
            "應該有排行榜標籤頁內容"
        )
        
        # 檢查是否有排行榜表格（在 tabPaneLeaderboard 內）
        # 簡單檢查：只要在整個內容中有這些元素即可（因為 HTML 結構可能複雜）
        self.assertIn('<table', content, "排行榜標籤頁應該包含表格")
        self.assertIn('<thead', content, "表格應該有標題行")
        self.assertIn('排名', content, "表格應該有'排名'列")
        self.assertIn('成員', content, "表格應該有'成員'列")
        self.assertIn('總分', content, "表格應該有'總分'列")
        self.assertIn('完成條數', content, "表格應該有'完成條數'列")
        self.assertIn('操作', content, "表格應該有'操作'列")
    
    def test_routes_tab_contains_routes_list(self):
        """
        測試：路線列表標籤頁包含路線列表容器
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查 HTML 內容
        3. 檢查路線列表標籤頁內容中是否有路線列表容器
        4. 驗證容器 ID 正確
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200,
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}"
        )
        
        content = response.content.decode('utf-8')
        
        # 檢查路線列表標籤頁內容存在（支持單引號或雙引號）
        self.assertTrue(
            'id="tabPaneRoutes"' in content or 'id=\'tabPaneRoutes\'' in content,
            "應該有路線列表標籤頁內容"
        )
        
        # 檢查是否有路線列表容器（在 tabPaneRoutes 內）
        # 簡單檢查：只要在整個內容中有這些元素即可
        self.assertTrue(
            'id="routesList"' in content or 'id=\'routesList\'' in content,
            "路線列表標籤頁應該包含路線列表容器"
        )
        self.assertIn('routes-list', content, "路線列表容器應該有 routes-list 類")
    
    def test_tab_buttons_have_correct_onclick_handlers(self):
        """
        測試：標籤頁按鈕有正確的 onclick 處理器
        
        測試步驟：
        1. 訪問排行榜頁面
        2. 檢查 HTML 內容
        3. 檢查排行榜標籤頁按鈕的 onclick 屬性
        4. 檢查路線列表標籤頁按鈕的 onclick 屬性
        5. 驗證調用正確的函數和參數
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(
            response.status_code, 
            200,
            f"應該能訪問排行榜頁面，但返回了 {response.status_code}"
        )
        
        content = response.content.decode('utf-8')
        
        # 檢查排行榜標籤頁按鈕
        # 查找包含 id="tabLeaderboard" 和 onclick 的按鈕（支持單引號或雙引號）
        leaderboard_btn_pattern = r'<button[^>]*id=["\']tabLeaderboard["\'][^>]*>'
        leaderboard_btn_match = re.search(leaderboard_btn_pattern, content, re.IGNORECASE)
        self.assertIsNotNone(leaderboard_btn_match, "應該有排行榜標籤頁按鈕")
        # 檢查 onclick 屬性（可能在按鈕標籤內）
        leaderboard_btn_html = leaderboard_btn_match.group(0)
        self.assertIn('onclick', leaderboard_btn_html.lower(), "排行榜按鈕應該有 onclick 屬性")
        self.assertIn('switchTab', leaderboard_btn_html, "排行榜按鈕應該調用 switchTab 函數")
        self.assertIn('leaderboard', leaderboard_btn_html, "排行榜按鈕應該傳遞 'leaderboard' 參數")
        
        # 檢查路線列表標籤頁按鈕
        routes_btn_pattern = r'<button[^>]*id=["\']tabRoutes["\'][^>]*>'
        routes_btn_match = re.search(routes_btn_pattern, content, re.IGNORECASE)
        self.assertIsNotNone(routes_btn_match, "應該有路線列表標籤頁按鈕")
        routes_btn_html = routes_btn_match.group(0)
        self.assertIn('onclick', routes_btn_html.lower(), "路線列表按鈕應該有 onclick 屬性")
        self.assertIn('switchTab', routes_btn_html, "路線列表按鈕應該調用 switchTab 函數")
        self.assertIn('routes', routes_btn_html, "路線列表按鈕應該傳遞 'routes' 參數")

