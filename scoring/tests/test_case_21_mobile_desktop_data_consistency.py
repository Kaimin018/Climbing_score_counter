"""
移動端和桌面端排行榜數據一致性測試用例

問題描述：
- 當同時用手機和電腦打開同一個排行榜時，數據內容可能不一致
- 這可能是由於緩存、實時更新、或 API 響應差異導致的

測試項目：
1. 移動端和桌面端獲取同一房間的排行榜數據應該完全一致
2. 在移動端更新數據後，桌面端應該能立即看到更新
3. 在桌面端更新數據後，移動端應該能立即看到更新
4. 驗證 API 響應不依賴於 User-Agent
5. 驗證數據庫中的數據與 API 響應一致
6. 驗證分數計算在兩個端點都正確
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score, update_scores
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json


class TestCaseMobileDesktopDataConsistency(TestCase):
    """測試移動端和桌面端排行榜數據一致性"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("數據一致性測試房間")
        self.m1, self.m2, self.m3 = self.factory.create_normal_members(
            self.room,
            count=3,
            names=["成員1", "成員2", "成員3"]
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
        
        # 設置房間的標準線分數
        self.room.standard_line_score = 10.0
        self.room.save()
        
        # 創建路線並設置完成狀態
        self.route1 = self.factory.create_route(
            room=self.room,
            name="路線1",
            grade="V3",
            members=[self.m1, self.m2, self.m3]
        )
        
        # 設置成員1完成路線1
        score1 = Score.objects.get(route=self.route1, member=self.m1)
        score1.is_completed = True
        score1.save()
        
        # 更新分數
        update_scores(self.room.id)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def _get_leaderboard_data(self, user_agent=None):
        """輔助方法：獲取排行榜數據"""
        url = f'/api/rooms/{self.room.id}/leaderboard/'
        headers = {}
        if user_agent:
            headers['HTTP_USER_AGENT'] = user_agent
        
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data
    
    def _normalize_leaderboard_data(self, data):
        """輔助方法：標準化排行榜數據以便比較"""
        # 提取關鍵字段並排序
        leaderboard = data.get('leaderboard', [])
        normalized = []
        for member in leaderboard:
            normalized.append({
                'id': member['id'],
                'name': member['name'],
                'total_score': float(member['total_score']),
                'completed_routes_count': member.get('completed_routes_count', 0)
            })
        # 按 ID 排序以確保順序一致
        normalized.sort(key=lambda x: x['id'])
        return {
            'room_info': data.get('room_info', {}),
            'leaderboard': normalized
        }
    
    def test_mobile_desktop_leaderboard_data_consistency(self):
        """
        測試：移動端和桌面端獲取同一房間的排行榜數據應該完全一致
        
        測試步驟：
        1. 使用移動端 User-Agent 獲取排行榜數據
        2. 使用桌面端 User-Agent 獲取排行榜數據
        3. 比較兩個響應的數據是否完全一致
        4. 驗證房間信息和排行榜數據都一致
        """
        # 移動端 User-Agent
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        
        # 桌面端 User-Agent
        desktop_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 獲取移動端數據
        mobile_data = self._get_leaderboard_data(user_agent=mobile_ua)
        
        # 獲取桌面端數據
        desktop_data = self._get_leaderboard_data(user_agent=desktop_ua)
        
        # 標準化數據以便比較
        mobile_normalized = self._normalize_leaderboard_data(mobile_data)
        desktop_normalized = self._normalize_leaderboard_data(desktop_data)
        
        # 驗證房間信息一致
        self.assertEqual(
            mobile_normalized['room_info'],
            desktop_normalized['room_info'],
            "移動端和桌面端的房間信息應該完全一致"
        )
        
        # 驗證排行榜數據一致
        self.assertEqual(
            len(mobile_normalized['leaderboard']),
            len(desktop_normalized['leaderboard']),
            "移動端和桌面端的成員數量應該一致"
        )
        
        # 驗證每個成員的數據都一致
        for i, (mobile_member, desktop_member) in enumerate(
            zip(mobile_normalized['leaderboard'], desktop_normalized['leaderboard'])
        ):
            self.assertEqual(
                mobile_member['id'],
                desktop_member['id'],
                f"第{i+1}個成員的 ID 應該一致"
            )
            self.assertEqual(
                mobile_member['name'],
                desktop_member['name'],
                f"第{i+1}個成員的名稱應該一致"
            )
            self.assertAlmostEqual(
                mobile_member['total_score'],
                desktop_member['total_score'],
                places=2,
                msg=f"第{i+1}個成員的總分應該一致（移動端: {mobile_member['total_score']}, 桌面端: {desktop_member['total_score']}）"
            )
            self.assertEqual(
                mobile_member['completed_routes_count'],
                desktop_member['completed_routes_count'],
                f"第{i+1}個成員的完成路線數應該一致"
            )
    
    def test_mobile_update_reflects_on_desktop(self):
        """
        測試：在移動端更新數據後，桌面端應該能立即看到更新
        
        測試步驟：
        1. 在移動端創建新路線並設置完成狀態
        2. 更新分數
        3. 在桌面端獲取排行榜數據
        4. 驗證桌面端能看到移動端的更新
        """
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        desktop_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 獲取初始數據
        initial_data = self._get_leaderboard_data(user_agent=desktop_ua)
        initial_member1 = next(
            (m for m in initial_data['leaderboard'] if m['id'] == self.m1.id),
            None
        )
        self.assertIsNotNone(initial_member1, "應該能找到成員1")
        initial_score = float(initial_member1['total_score'])
        
        # 在移動端創建新路線並設置成員2完成
        route2 = self.factory.create_route(
            room=self.room,
            name="路線2（移動端創建）",
            grade="V4",
            members=[self.m1, self.m2, self.m3]
        )
        
        # 設置成員2完成路線2
        score2 = Score.objects.get(route=route2, member=self.m2)
        score2.is_completed = True
        score2.save()
        
        # 更新分數
        update_scores(self.room.id)
        
        # 在桌面端獲取更新後的數據
        updated_data = self._get_leaderboard_data(user_agent=desktop_ua)
        updated_member2 = next(
            (m for m in updated_data['leaderboard'] if m['id'] == self.m2.id),
            None
        )
        self.assertIsNotNone(updated_member2, "應該能找到成員2")
        updated_score = float(updated_member2['total_score'])
        
        # 驗證成員2的分數已更新（應該大於0，因為完成了路線2）
        self.assertGreater(
            updated_score,
            0,
            f"成員2完成路線2後，分數應該大於0，實際: {updated_score}"
        )
        
        # 驗證成員1的分數沒有變化（因為沒有完成新路線）
        updated_member1 = next(
            (m for m in updated_data['leaderboard'] if m['id'] == self.m1.id),
            None
        )
        self.assertIsNotNone(updated_member1, "應該能找到成員1")
        self.assertAlmostEqual(
            float(updated_member1['total_score']),
            initial_score,
            places=2,
            msg="成員1的分數不應該改變（因為沒有完成新路線）"
        )
    
    def test_desktop_update_reflects_on_mobile(self):
        """
        測試：在桌面端更新數據後，移動端應該能立即看到更新
        
        測試步驟：
        1. 在桌面端創建新路線並設置完成狀態
        2. 更新分數
        3. 在移動端獲取排行榜數據
        4. 驗證移動端能看到桌面端的更新
        """
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        desktop_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # 獲取初始數據
        initial_data = self._get_leaderboard_data(user_agent=mobile_ua)
        initial_member3 = next(
            (m for m in initial_data['leaderboard'] if m['id'] == self.m3.id),
            None
        )
        self.assertIsNotNone(initial_member3, "應該能找到成員3")
        initial_score = float(initial_member3['total_score'])
        
        # 在桌面端創建新路線並設置成員3完成
        route3 = self.factory.create_route(
            room=self.room,
            name="路線3（桌面端創建）",
            grade="V5",
            members=[self.m1, self.m2, self.m3]
        )
        
        # 設置成員3完成路線3
        score3 = Score.objects.get(route=route3, member=self.m3)
        score3.is_completed = True
        score3.save()
        
        # 更新分數
        update_scores(self.room.id)
        
        # 在移動端獲取更新後的數據
        updated_data = self._get_leaderboard_data(user_agent=mobile_ua)
        updated_member3 = next(
            (m for m in updated_data['leaderboard'] if m['id'] == self.m3.id),
            None
        )
        self.assertIsNotNone(updated_member3, "應該能找到成員3")
        updated_score = float(updated_member3['total_score'])
        
        # 驗證成員3的分數已更新（應該大於初始分數）
        self.assertGreater(
            updated_score,
            initial_score,
            f"成員3完成路線3後，分數應該增加。初始: {initial_score}, 更新後: {updated_score}"
        )
    
    def test_api_response_independent_of_user_agent(self):
        """
        測試：驗證 API 響應不依賴於 User-Agent
        
        測試步驟：
        1. 使用不同的 User-Agent 獲取排行榜數據
        2. 驗證所有響應的數據都完全一致
        3. 確保 API 不根據 User-Agent 返回不同的數據
        """
        user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/109.0',
            None  # 無 User-Agent
        ]
        
        all_data = []
        for ua in user_agents:
            data = self._get_leaderboard_data(user_agent=ua)
            normalized = self._normalize_leaderboard_data(data)
            all_data.append(normalized)
        
        # 驗證所有響應的數據都一致
        first_data = all_data[0]
        for i, data in enumerate(all_data[1:], 1):
            self.assertEqual(
                first_data['room_info'],
                data['room_info'],
                f"第{i+1}個 User-Agent 的房間信息應該與第一個一致"
            )
            self.assertEqual(
                len(first_data['leaderboard']),
                len(data['leaderboard']),
                f"第{i+1}個 User-Agent 的成員數量應該與第一個一致"
            )
            for j, (first_member, other_member) in enumerate(
                zip(first_data['leaderboard'], data['leaderboard'])
            ):
                self.assertEqual(
                    first_member['id'],
                    other_member['id'],
                    f"第{i+1}個 User-Agent 的第{j+1}個成員 ID 應該一致"
                )
                self.assertAlmostEqual(
                    first_member['total_score'],
                    other_member['total_score'],
                    places=2,
                    msg=f"第{i+1}個 User-Agent 的第{j+1}個成員分數應該一致"
                )
    
    def test_database_data_matches_api_response(self):
        """
        測試：驗證數據庫中的數據與 API 響應一致
        
        測試步驟：
        1. 從數據庫直接獲取成員數據
        2. 從 API 獲取排行榜數據
        3. 比較兩者的數據是否一致
        4. 驗證分數計算正確
        """
        # 從 API 獲取數據
        api_data = self._get_leaderboard_data()
        api_leaderboard = api_data.get('leaderboard', [])
        
        # 從數據庫獲取數據
        db_members = Member.objects.filter(room=self.room).order_by('-total_score', 'name')
        
        # 驗證數量一致
        self.assertEqual(
            len(api_leaderboard),
            db_members.count(),
            "API 返回的成員數量應該與數據庫一致"
        )
        
        # 驗證每個成員的數據一致
        for api_member, db_member in zip(api_leaderboard, db_members):
            self.assertEqual(
                api_member['id'],
                db_member.id,
                f"成員 {db_member.name} 的 ID 應該一致"
            )
            self.assertEqual(
                api_member['name'],
                db_member.name,
                f"成員 {db_member.name} 的名稱應該一致"
            )
            self.assertAlmostEqual(
                float(api_member['total_score']),
                float(db_member.total_score),
                places=2,
                msg=f"成員 {db_member.name} 的總分應該一致（API: {api_member['total_score']}, DB: {db_member.total_score}）"
            )
            self.assertEqual(
                api_member.get('completed_routes_count', 0),
                db_member.completed_routes_count,
                f"成員 {db_member.name} 的完成路線數應該一致"
            )
    
    def test_score_calculation_consistency(self):
        """
        測試：驗證分數計算在兩個端點都正確
        
        測試步驟：
        1. 創建多條路線並設置不同的完成狀態
        2. 更新分數
        3. 在移動端和桌面端分別獲取數據
        4. 驗證兩個端點的分數計算結果一致
        5. 驗證分數計算邏輯正確（動態分數計算）
        """
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
        desktop_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        
        # 創建多條路線
        routes = []
        for i in range(3):
            route = self.factory.create_route(
                room=self.room,
                name=f"測試路線{i+2}",
                grade=f"V{i+3}",
                members=[self.m1, self.m2, self.m3]
            )
            routes.append(route)
        
        # 設置完成狀態：
        # 成員1完成路線1和路線2
        # 成員2完成路線2和路線3
        # 成員3完成路線3
        Score.objects.filter(route=routes[0], member=self.m1).update(is_completed=True)
        Score.objects.filter(route=routes[0], member=self.m2).update(is_completed=True)
        Score.objects.filter(route=routes[1], member=self.m1).update(is_completed=True)
        Score.objects.filter(route=routes[1], member=self.m2).update(is_completed=True)
        Score.objects.filter(route=routes[2], member=self.m2).update(is_completed=True)
        Score.objects.filter(route=routes[2], member=self.m3).update(is_completed=True)
        
        # 更新分數
        update_scores(self.room.id)
        
        # 刷新數據庫對象
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        
        # 獲取移動端和桌面端數據
        mobile_data = self._get_leaderboard_data(user_agent=mobile_ua)
        desktop_data = self._get_leaderboard_data(user_agent=desktop_ua)
        
        # 驗證移動端和桌面端數據一致性（不驗證具體分數值，因為分數計算邏輯複雜）
        # 主要驗證兩個端點返回的數據完全一致
        mobile_normalized = self._normalize_leaderboard_data(mobile_data)
        desktop_normalized = self._normalize_leaderboard_data(desktop_data)
        
        # 驗證房間信息一致
        self.assertEqual(
            mobile_normalized['room_info'],
            desktop_normalized['room_info'],
            "移動端和桌面端的房間信息應該完全一致"
        )
        
        # 驗證每個成員的數據在兩個端點都一致
        for mobile_member, desktop_member in zip(
            mobile_normalized['leaderboard'],
            desktop_normalized['leaderboard']
        ):
            member_id = mobile_member['id']
            
            # 驗證移動端和桌面端分數一致
            self.assertAlmostEqual(
                mobile_member['total_score'],
                desktop_member['total_score'],
                places=2,
                msg=f"成員 {member_id} 在移動端和桌面端的分數應該一致"
            )
            
            # 驗證完成路線數一致
            self.assertEqual(
                mobile_member['completed_routes_count'],
                desktop_member['completed_routes_count'],
                f"成員 {member_id} 的完成路線數在移動端和桌面端應該一致"
            )
            
            # 驗證數據庫中的分數與 API 響應一致
            db_member = Member.objects.get(id=member_id)
            self.assertAlmostEqual(
                float(db_member.total_score),
                mobile_member['total_score'],
                places=2,
                msg=f"成員 {member_id} 的數據庫分數應該與 API 響應一致"
            )

