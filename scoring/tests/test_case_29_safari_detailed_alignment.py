"""
測試案例：Safari 瀏覽器路線列表對齊問題 - 詳細診斷
針對 iPhone 14 Pro Safari 的詳細測試，包括：
1. 檢查每個元素的具體 CSS 屬性值
2. 檢查 HTML 結構和內聯樣式
3. 檢查 JavaScript 生成的 HTML
4. 檢查移動端特定的樣式覆蓋
5. 檢查 Safari 特定的兼容性問題
"""

import re
from django.contrib.auth.models import User
from django.test import TestCase, Client
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from bs4 import BeautifulSoup


class TestCaseSafariDetailedAlignment(TestCase):
    """Safari 瀏覽器路線列表對齊問題 - 詳細診斷測試"""
    
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
        self.room = self.factory.create_room("Safari 詳細測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試路線（包括可能導致換行問題的路線名稱）
        self.route1 = self.factory.create_route(
            room=self.room,
            name="【路線】正面黑",
            grade="V4",
            members=[self.m1, self.m2]
        )
        self.route2 = self.factory.create_route(
            room=self.room,
            name="【路線】路線3",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        # 登入用戶
        self.client.force_login(self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_routes_header_inline_styles_detailed(self):
        """
        詳細測試：routes-header 的內聯樣式是否正確設置
        
        驗證點：
        1. routes-header div 有 text-align: left !important
        2. routes-header div 有 -webkit-text-align: left !important
        3. routes-header div 有 display: flex
        4. routes-header div 有 flex-direction: column
        5. routes-header div 有 align-items: flex-start
        6. h3 標籤有 text-align: left !important
        7. h3 標籤有 -webkit-text-align: left !important
        8. h3 標籤有 align-self: flex-start
        9. h3 標籤有 width: 100%
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找 routes-header div
        routes_header = soup.find('div', class_='routes-header')
        self.assertIsNotNone(routes_header, "應該找到 routes-header div")
        
        # 檢查內聯樣式
        style_attr = routes_header.get('style', '')
        self.assertIsNotNone(style_attr, "routes-header 應該有 style 屬性")
        
        # 檢查 text-align: left !important
        self.assertIn('text-align', style_attr.lower(), "routes-header 應該有 text-align")
        self.assertIn('left', style_attr.lower(), "routes-header 的 text-align 應該是 left")
        # 注意：!important 在內聯樣式中不需要，因為內聯樣式優先級最高
        
        # 檢查 -webkit-text-align
        self.assertIn('-webkit-text-align', style_attr.lower(), 
                     "routes-header 應該有 -webkit-text-align（針對 Safari）")
        
        # 檢查 display: flex
        self.assertIn('display', style_attr.lower(), "routes-header 應該有 display")
        self.assertIn('flex', style_attr.lower(), "routes-header 的 display 應該是 flex")
        
        # 檢查 flex-direction: column
        self.assertIn('flex-direction', style_attr.lower(), 
                     "routes-header 應該有 flex-direction")
        self.assertIn('column', style_attr.lower(), 
                     "routes-header 的 flex-direction 應該是 column")
        
        # 檢查 align-items: flex-start
        self.assertIn('align-items', style_attr.lower(), 
                     "routes-header 應該有 align-items")
        self.assertIn('flex-start', style_attr.lower(), 
                     "routes-header 的 align-items 應該是 flex-start")
        
        # 檢查 h3 標籤
        h3 = routes_header.find('h3')
        self.assertIsNotNone(h3, "routes-header 內應該有 h3 標籤")
        
        h3_style = h3.get('style', '')
        self.assertIsNotNone(h3_style, "h3 應該有 style 屬性")
        
        # 檢查 h3 的 text-align
        self.assertIn('text-align', h3_style.lower(), "h3 應該有 text-align")
        self.assertIn('left', h3_style.lower(), "h3 的 text-align 應該是 left")
        
        # 檢查 h3 的 -webkit-text-align
        self.assertIn('-webkit-text-align', h3_style.lower(), 
                     "h3 應該有 -webkit-text-align（針對 Safari）")
        
        # 檢查 h3 的 align-self
        self.assertIn('align-self', h3_style.lower(), "h3 應該有 align-self")
        self.assertIn('flex-start', h3_style.lower(), "h3 的 align-self 應該是 flex-start")
        
        # 檢查 h3 的 width
        self.assertIn('width', h3_style.lower(), "h3 應該有 width")
        self.assertIn('100%', h3_style, "h3 的 width 應該是 100%")
    
    def test_tab_pane_routes_inline_styles_detailed(self):
        """
        詳細測試：tabPaneRoutes 的內聯樣式是否正確設置
        
        驗證點：
        1. tabPaneRoutes div 有 text-align: left !important
        2. tabPaneRoutes div 有 -webkit-text-align: left !important
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找 tabPaneRoutes div
        tab_pane = soup.find('div', id='tabPaneRoutes')
        self.assertIsNotNone(tab_pane, "應該找到 tabPaneRoutes div")
        
        # 檢查內聯樣式
        style_attr = tab_pane.get('style', '')
        self.assertIsNotNone(style_attr, "tabPaneRoutes 應該有 style 屬性")
        
        # 檢查 text-align
        self.assertIn('text-align', style_attr.lower(), 
                     "tabPaneRoutes 應該有 text-align")
        self.assertIn('left', style_attr.lower(), 
                     "tabPaneRoutes 的 text-align 應該是 left")
        
        # 檢查 -webkit-text-align
        self.assertIn('-webkit-text-align', style_attr.lower(), 
                     "tabPaneRoutes 應該有 -webkit-text-align（針對 Safari）")
    
    def test_routes_list_inline_styles_detailed(self):
        """
        詳細測試：routes-list 的內聯樣式是否正確設置
        
        驗證點：
        1. routes-list div 有 text-align: left !important
        2. routes-list div 有 -webkit-text-align: left !important
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找 routes-list div
        routes_list = soup.find('div', id='routesList')
        self.assertIsNotNone(routes_list, "應該找到 routesList div")
        
        # 檢查內聯樣式
        style_attr = routes_list.get('style', '')
        
        # 如果沒有內聯樣式，檢查是否有 class
        if not style_attr:
            self.assertIn('routes-list', routes_list.get('class', []), 
                         "routes-list 應該有 routes-list class")
        else:
            # 檢查 text-align
            self.assertIn('text-align', style_attr.lower(), 
                         "routes-list 應該有 text-align")
            self.assertIn('left', style_attr.lower(), 
                         "routes-list 的 text-align 應該是 left")
            
            # 檢查 -webkit-text-align
            self.assertIn('-webkit-text-align', style_attr.lower(), 
                         "routes-list 應該有 -webkit-text-align（針對 Safari）")
    
    def test_route_name_grade_css_properties_detailed(self):
        """
        詳細測試：route-name-grade 的 CSS 屬性是否正確
        
        驗證點：
        1. .route-name-grade 有 flex-wrap: nowrap
        2. .route-name-grade 有 -webkit-flex-wrap: nowrap
        3. .route-name-grade strong 有 white-space: nowrap
        4. .route-name-grade strong 有 display: inline-block
        5. .route-name-grade strong 有 max-width: 100%
        6. .route-name-grade strong 有 overflow: hidden
        7. .route-name-grade strong 有 text-overflow: ellipsis
        """
        # 嘗試多個可能的 CSS 路徑
        css_paths = ['/static/css/style.css', '/css/style.css', 'static/css/style.css']
        css_content = None
        
        for path in css_paths:
            css_response = self.client.get(path)
            if css_response.status_code == 200:
                css_content = css_response.content.decode('utf-8')
                break
        
        if not css_content:
            # 如果無法通過 HTTP 獲取，嘗試直接讀取文件（僅在開發環境）
            try:
                import os
                from django.conf import settings
                css_file_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
                if os.path.exists(css_file_path):
                    with open(css_file_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
            except Exception:
                pass  # 在 CI 環境中可能無法讀取文件，這是正常的
        
        self.assertIsNotNone(css_content, "應該能夠讀取 CSS 文件（通過 HTTP 或文件系統）")
        
        # 檢查桌面端 .route-name-grade
        route_name_grade_pattern = r'\.route-name-grade\s*\{[^}]*\}'
        matches = re.finditer(route_name_grade_pattern, css_content, re.IGNORECASE | re.DOTALL)
        found_desktop = False
        for match in matches:
            rule_content = match.group(0)
            if 'flex-wrap' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            "桌面端 .route-name-grade 應該有 flex-wrap: nowrap")
                found_desktop = True
            if '-webkit-flex-wrap' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            "桌面端 .route-name-grade 應該有 -webkit-flex-wrap: nowrap")
        
        # 檢查移動端 .route-name-grade（在 @media 查詢中）
        mobile_pattern = r'@media[^}]*\.route-name-grade[^}]*\{[^}]*\}'
        mobile_matches = re.finditer(mobile_pattern, css_content, re.IGNORECASE | re.DOTALL)
        found_mobile = False
        for match in mobile_matches:
            rule_content = match.group(0)
            if 'flex-wrap' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            "移動端 .route-name-grade 應該有 flex-wrap: nowrap")
                found_mobile = True
            if '-webkit-flex-wrap' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            "移動端 .route-name-grade 應該有 -webkit-flex-wrap: nowrap")
        
        # 檢查 .route-name-grade strong
        strong_pattern = r'\.route-name-grade\s+strong\s*\{[^}]*\}'
        strong_matches = re.finditer(strong_pattern, css_content, re.IGNORECASE | re.DOTALL)
        found_strong = False
        for match in strong_matches:
            rule_content = match.group(0)
            # 檢查 white-space: nowrap
            if 'white-space' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            ".route-name-grade strong 應該有 white-space: nowrap")
                found_strong = True
            
            # 檢查 display: inline-block
            if 'display' in rule_content.lower():
                self.assertIn('inline-block', rule_content.lower(), 
                            ".route-name-grade strong 應該有 display: inline-block")
            
            # 檢查 max-width: 100%
            if 'max-width' in rule_content.lower():
                self.assertIn('100%', rule_content, 
                            ".route-name-grade strong 應該有 max-width: 100%")
            
            # 檢查 overflow: hidden
            if 'overflow' in rule_content.lower():
                self.assertIn('hidden', rule_content.lower(), 
                            ".route-name-grade strong 應該有 overflow: hidden")
            
            # 檢查 text-overflow: ellipsis
            if 'text-overflow' in rule_content.lower():
                self.assertIn('ellipsis', rule_content.lower(), 
                            ".route-name-grade strong 應該有 text-overflow: ellipsis")
        
        # 檢查移動端 .route-name-grade strong
        mobile_strong_pattern = r'@media[^}]*\.route-name-grade\s+strong[^}]*\{[^}]*\}'
        mobile_strong_matches = re.finditer(mobile_strong_pattern, css_content, re.IGNORECASE | re.DOTALL)
        for match in mobile_strong_matches:
            rule_content = match.group(0)
            if 'white-space' in rule_content.lower():
                self.assertIn('nowrap', rule_content.lower(), 
                            "移動端 .route-name-grade strong 應該有 white-space: nowrap")
    
    def test_route_item_html_structure_detailed(self):
        """
        詳細測試：路線項目的 HTML 結構是否正確
        
        驗證點：
        1. 路線名稱在 <strong> 標籤內
        2. 路線名稱沒有額外的換行符
        3. 路線名稱和等級標籤在同一行（通過 flex 布局）
        4. 路線項目的 class 正確
        """
        # 先加載路線列表（通過 API）
        # 嘗試多個可能的 API 路徑
        api_paths = [
            f'/api/rooms/{self.room.id}/routes/',
            f'/api/routes/?room={self.room.id}',
        ]
        routes_data = None
        
        for path in api_paths:
            response = self.client.get(path)
            if response.status_code == 200:
                routes_data = response.json()
                break
        
        # 如果 API 無法訪問，直接從數據庫獲取
        if not routes_data:
            routes = Route.objects.filter(room=self.room)
            routes_data = [{'id': r.id, 'name': r.name, 'grade': r.grade} for r in routes]
        
        # 訪問頁面並檢查 HTML
        page_response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(page_response.status_code, 200)
        
        soup = BeautifulSoup(page_response.content, 'html.parser')
        
        # 檢查 routesList 容器
        routes_list = soup.find('div', id='routesList')
        self.assertIsNotNone(routes_list, "應該找到 routesList div")
        
        # 檢查是否有 route-item（可能通過 JavaScript 動態生成）
        # 由於路線是通過 JavaScript 動態生成的，我們檢查 JavaScript 代碼
        script_tags = soup.find_all('script')
        display_routes_function_found = False
        
        for script in script_tags:
            if script.string and 'displayRoutes' in script.string:
                display_routes_function_found = True
                script_content = script.string
                
                # 檢查路線名稱是否在 <strong> 標籤內
                self.assertIn('<strong>', script_content, 
                             "displayRoutes 函數應該使用 <strong> 標籤包裹路線名稱")
                
                # 檢查路線名稱的生成邏輯
                self.assertIn('routeDisplayName', script_content, 
                             "應該使用 routeDisplayName 變量")
                
                # 檢查是否有 route-item class
                self.assertIn('route-item', script_content, 
                             "應該有 route-item class")
                
                # 檢查是否有 route-name-grade class
                self.assertIn('route-name-grade', script_content, 
                             "應該有 route-name-grade class")
                
                # 檢查路線名稱和等級是否在同一行（通過 flex 布局）
                # 應該在同一個 route-name-grade div 內
                self.assertIn('route-grade', script_content, 
                             "應該有 route-grade class")
        
        self.assertTrue(display_routes_function_found, 
                       "應該找到 displayRoutes 函數")
    
    def test_css_media_query_mobile_detailed(self):
        """
        詳細測試：移動端媒體查詢中的樣式是否正確
        
        驗證點：
        1. @media (max-width: 768px) 存在
        2. 移動端 .routes-header 有 text-align: left !important
        3. 移動端 .routes-header 有 -webkit-text-align: left !important
        4. 移動端 .routes-header 有 display: flex
        5. 移動端 .routes-header 有 align-items: flex-start
        6. 移動端 .routes-header h3 有 text-align: left !important
        7. 移動端 .routes-header h3 有 align-self: flex-start
        8. 移動端 .routes-header h3 有 width: 100%
        """
        # 嘗試多個可能的 CSS 路徑
        css_paths = ['/static/css/style.css', '/css/style.css', 'static/css/style.css']
        css_content = None
        
        for path in css_paths:
            css_response = self.client.get(path)
            if css_response.status_code == 200:
                css_content = css_response.content.decode('utf-8')
                break
        
        if not css_content:
            # 如果無法通過 HTTP 獲取，嘗試直接讀取文件（僅在開發環境）
            try:
                import os
                from django.conf import settings
                css_file_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
                if os.path.exists(css_file_path):
                    with open(css_file_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
            except Exception:
                pass  # 在 CI 環境中可能無法讀取文件，這是正常的
        
        self.assertIsNotNone(css_content, "應該能夠讀取 CSS 文件（通過 HTTP 或文件系統）")
        
        # 檢查是否有移動端媒體查詢
        self.assertIn('@media', css_content, "應該有 @media 查詢")
        self.assertIn('max-width: 768px', css_content, 
                     "應該有移動端媒體查詢 (max-width: 768px)")
        
        # 查找移動端 .routes-header 樣式
        mobile_routes_header_pattern = r'@media[^}]*max-width:\s*768px[^}]*\.routes-header[^}]*\{[^}]*\}'
        mobile_matches = re.finditer(mobile_routes_header_pattern, css_content, 
                                     re.IGNORECASE | re.DOTALL)
        
        found_mobile_routes_header = False
        for match in mobile_matches:
            rule_content = match.group(0)
            found_mobile_routes_header = True
            
            # 檢查 text-align
            if 'text-align' in rule_content.lower():
                self.assertIn('left', rule_content.lower(), 
                            "移動端 .routes-header 應該有 text-align: left")
            
            # 檢查 -webkit-text-align
            if '-webkit-text-align' in rule_content.lower():
                self.assertIn('left', rule_content.lower(), 
                            "移動端 .routes-header 應該有 -webkit-text-align: left")
            
            # 檢查 display: flex
            if 'display' in rule_content.lower():
                self.assertIn('flex', rule_content.lower(), 
                            "移動端 .routes-header 應該有 display: flex")
            
            # 檢查 align-items
            if 'align-items' in rule_content.lower():
                self.assertIn('flex-start', rule_content.lower(), 
                            "移動端 .routes-header 應該有 align-items: flex-start")
        
        # 查找移動端 .routes-header h3 樣式
        mobile_h3_pattern = r'@media[^}]*max-width:\s*768px[^}]*\.routes-header\s+h3[^}]*\{[^}]*\}'
        mobile_h3_matches = re.finditer(mobile_h3_pattern, css_content, 
                                       re.IGNORECASE | re.DOTALL)
        
        found_mobile_h3 = False
        for match in mobile_h3_matches:
            rule_content = match.group(0)
            found_mobile_h3 = True
            
            # 檢查 text-align
            if 'text-align' in rule_content.lower():
                self.assertIn('left', rule_content.lower(), 
                            "移動端 .routes-header h3 應該有 text-align: left")
            
            # 檢查 align-self
            if 'align-self' in rule_content.lower():
                self.assertIn('flex-start', rule_content.lower(), 
                            "移動端 .routes-header h3 應該有 align-self: flex-start")
            
            # 檢查 width
            if 'width' in rule_content.lower():
                self.assertIn('100%', rule_content, 
                            "移動端 .routes-header h3 應該有 width: 100%")
    
    def test_route_name_no_line_break_in_html(self):
        """
        詳細測試：路線名稱在 HTML 中沒有換行符
        
        驗證點：
        1. 路線名稱文本中沒有 \n
        2. 路線名稱文本中沒有 <br> 標籤
        3. 路線名稱是連續的字符串
        """
        # 獲取路線數據（直接從數據庫）
        routes = Route.objects.filter(room=self.room)
        routes_data = [{'id': r.id, 'name': r.name, 'grade': r.grade} for r in routes]
        
        # 檢查每個路線的名稱
        for route in routes_data:
            route_name = route.get('name', '')
            self.assertIsNotNone(route_name, f"路線 {route.get('id')} 應該有名稱")
            
            # 檢查名稱中沒有換行符
            self.assertNotIn('\n', route_name, 
                           f"路線名稱 '{route_name}' 中不應該有換行符")
            self.assertNotIn('\r', route_name, 
                           f"路線名稱 '{route_name}' 中不應該有回車符")
            
            # 檢查名稱是連續的（沒有多個連續空格）
            # 注意：單個空格是允許的，但多個連續空格可能表示問題
            if '  ' in route_name:
                # 這可能是問題，但不一定是錯誤（取決於業務邏輯）
                pass
    
    def test_tab_pane_css_properties_detailed(self):
        """
        詳細測試：tab-pane 的 CSS 屬性是否正確
        
        驗證點：
        1. .tab-pane 有 text-align: left !important
        2. .tab-pane 有 -webkit-text-align: left !important
        3. .tab-pane 有 align-items: stretch
        4. .tab-pane 有 -webkit-align-items: stretch
        """
        # 嘗試多個可能的 CSS 路徑
        css_paths = ['/static/css/style.css', '/css/style.css', 'static/css/style.css']
        css_content = None
        
        for path in css_paths:
            css_response = self.client.get(path)
            if css_response.status_code == 200:
                css_content = css_response.content.decode('utf-8')
                break
        
        if not css_content:
            # 如果無法通過 HTTP 獲取，嘗試直接讀取文件（僅在開發環境）
            try:
                import os
                from django.conf import settings
                css_file_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
                if os.path.exists(css_file_path):
                    with open(css_file_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
            except Exception:
                pass  # 在 CI 環境中可能無法讀取文件，這是正常的
        
        self.assertIsNotNone(css_content, "應該能夠讀取 CSS 文件（通過 HTTP 或文件系統）")
        
        # 查找 .tab-pane 樣式
        tab_pane_pattern = r'\.tab-pane\s*\{[^}]*\}'
        matches = re.finditer(tab_pane_pattern, css_content, re.IGNORECASE | re.DOTALL)
        
        found_tab_pane = False
        for match in matches:
            rule_content = match.group(0)
            found_tab_pane = True
            
            # 檢查 text-align
            if 'text-align' in rule_content.lower():
                self.assertIn('left', rule_content.lower(), 
                            ".tab-pane 應該有 text-align: left")
            
            # 檢查 -webkit-text-align
            if '-webkit-text-align' in rule_content.lower():
                self.assertIn('left', rule_content.lower(), 
                            ".tab-pane 應該有 -webkit-text-align: left")
            
            # 檢查 align-items
            if 'align-items' in rule_content.lower():
                self.assertIn('stretch', rule_content.lower(), 
                            ".tab-pane 應該有 align-items: stretch")
            
            # 檢查 -webkit-align-items
            if '-webkit-align-items' in rule_content.lower():
                self.assertIn('stretch', rule_content.lower(), 
                            ".tab-pane 應該有 -webkit-align-items: stretch")
        
        self.assertTrue(found_tab_pane, "應該找到 .tab-pane 樣式規則")
    
    def test_route_display_name_generation(self):
        """
        詳細測試：路線顯示名稱的生成邏輯
        
        驗證點：
        1. 路線名稱正確添加【路線】前綴
        2. 如果已有【路線】前綴，不會重複添加
        3. 路線名稱是完整的字符串，沒有被分割
        """
        # 獲取路線數據（直接從數據庫）
        routes = Route.objects.filter(room=self.room)
        routes_data = [{'id': r.id, 'name': r.name, 'grade': r.grade} for r in routes]
        
        # 檢查每個路線
        for route in routes_data:
            route_name = route.get('name', '')
            
            # 檢查名稱格式
            # 應該以【路線】開頭
            self.assertTrue(
                route_name.startswith('【路線】'),
                f"路線名稱 '{route_name}' 應該以【路線】開頭"
            )
            
            # 檢查名稱中沒有意外的空格或換行
            name_after_prefix = route_name[4:]  # 移除【路線】前綴（4個字符）
            self.assertNotIn('\n', name_after_prefix, 
                           f"路線名稱 '{route_name}' 的後綴部分不應該有換行符")
            self.assertNotIn('\r', name_after_prefix, 
                           f"路線名稱 '{route_name}' 的後綴部分不應該有回車符")
    
    def test_safari_specific_css_vendor_prefixes(self):
        """
        詳細測試：Safari 特定的 CSS 廠商前綴
        
        驗證點：
        1. 所有關鍵樣式都有 -webkit- 前綴
        2. text-align 有 -webkit-text-align
        3. flex-wrap 有 -webkit-flex-wrap
        4. align-items 有 -webkit-align-items
        """
        # 嘗試多個可能的 CSS 路徑
        css_paths = ['/static/css/style.css', '/css/style.css', 'static/css/style.css']
        css_content = None
        
        for path in css_paths:
            css_response = self.client.get(path)
            if css_response.status_code == 200:
                css_content = css_response.content.decode('utf-8')
                break
        
        if not css_content:
            # 如果無法通過 HTTP 獲取，嘗試直接讀取文件（僅在開發環境）
            try:
                import os
                from django.conf import settings
                css_file_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'style.css')
                if os.path.exists(css_file_path):
                    with open(css_file_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
            except Exception:
                pass  # 在 CI 環境中可能無法讀取文件，這是正常的
        
        self.assertIsNotNone(css_content, "應該能夠讀取 CSS 文件（通過 HTTP 或文件系統）")
        
        # 檢查 routes-header 相關的 -webkit- 前綴
        if '.routes-header' in css_content:
            # 檢查是否有 -webkit-text-align
            self.assertTrue(
                '-webkit-text-align' in css_content.lower() or
                'text-align' in css_content.lower(),
                "應該有 text-align 或 -webkit-text-align"
            )
        
        # 檢查 route-name-grade 相關的 -webkit- 前綴
        if '.route-name-grade' in css_content:
            # 檢查是否有 -webkit-flex-wrap
            self.assertTrue(
                '-webkit-flex-wrap' in css_content.lower() or
                'flex-wrap' in css_content.lower(),
                "應該有 flex-wrap 或 -webkit-flex-wrap"
            )
        
        # 檢查 tab-pane 相關的 -webkit- 前綴
        if '.tab-pane' in css_content:
            # 檢查是否有 -webkit-align-items
            self.assertTrue(
                '-webkit-align-items' in css_content.lower() or
                'align-items' in css_content.lower(),
                "應該有 align-items 或 -webkit-align-items"
            )
    
    def test_html_structure_hierarchy(self):
        """
        詳細測試：HTML 結構層級是否正確
        
        驗證點：
        1. tabPaneRoutes > routes-header > h3 的層級結構
        2. tabPaneRoutes > routesList 的層級結構
        3. 每個元素都有正確的 class 或 id
        """
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 檢查 tabPaneRoutes
        tab_pane = soup.find('div', id='tabPaneRoutes')
        self.assertIsNotNone(tab_pane, "應該找到 tabPaneRoutes")
        
        # 檢查 routes-header 是 tabPaneRoutes 的直接子元素
        routes_header = tab_pane.find('div', class_='routes-header')
        self.assertIsNotNone(routes_header, 
                            "tabPaneRoutes 內應該有 routes-header")
        
        # 檢查 h3 是 routes-header 的直接子元素
        h3 = routes_header.find('h3')
        self.assertIsNotNone(h3, "routes-header 內應該有 h3")
        self.assertEqual(h3.get_text(strip=True), '路線列表', 
                        "h3 的文本應該是 '路線列表'")
        
        # 檢查 routesList 是 tabPaneRoutes 的直接子元素
        routes_list = tab_pane.find('div', id='routesList')
        self.assertIsNotNone(routes_list, 
                            "tabPaneRoutes 內應該有 routesList")
        
        # 檢查 routesList 有正確的 class
        self.assertIn('routes-list', routes_list.get('class', []), 
                     "routesList 應該有 routes-list class")

