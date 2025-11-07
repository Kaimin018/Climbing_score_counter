"""
手機刪除路線後立即刷新測試用例

測試項目：
1. 手機點擊刪除路線後，路線需要馬上重新整理，讓該路線消失
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json


class TestCaseMobileDeleteRoute(TestCase):
    """測試手機刪除路線後立即刷新功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("刪除路線測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_delete_route_immediately_refreshes_route_list(self):
        """測試：刪除路線後，路線列表立即更新，該路線消失"""
        # 創建兩條路線
        route1 = self.factory.create_route(
            room=self.room,
            name="路線1",
            grade="V3",
            members=[self.m1, self.m2]
        )
        route2 = self.factory.create_route(
            room=self.room,
            name="路線2",
            grade="V4",
            members=[self.m1, self.m2]
        )
        
        # 驗證初始狀態：應該有兩條路線
        url = f'/api/rooms/{self.room.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        routes = response.data.get('routes', [])
        self.assertEqual(len(routes), 2, "初始應該有兩條路線")
        
        # 驗證兩條路線都存在
        route_ids = [r['id'] for r in routes]
        self.assertIn(route1.id, route_ids, "路線1應該存在")
        self.assertIn(route2.id, route_ids, "路線2應該存在")
        
        # 刪除路線1
        delete_url = f'/api/routes/{route1.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_204_NO_CONTENT,
            f"刪除路線應該成功，但返回了 {delete_response.status_code}"
        )
        
        # 立即重新獲取路線列表，驗證路線1已消失
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        routes = response.data.get('routes', [])
        
        # 驗證路線1已消失，路線2仍然存在
        route_ids = [r['id'] for r in routes]
        self.assertNotIn(route1.id, route_ids, "路線1應該已被刪除")
        self.assertIn(route2.id, route_ids, "路線2應該仍然存在")
        self.assertEqual(len(routes), 1, "應該只剩下一條路線")
        
        # 驗證剩餘路線的資訊正確
        remaining_route = routes[0]
        self.assertEqual(remaining_route['id'], route2.id, "剩餘路線應該是路線2")
        self.assertEqual(remaining_route['name'], '路線2', "剩餘路線名稱應該是'路線2'")
    
    def test_delete_route_updates_leaderboard(self):
        """測試：刪除路線後，排行榜會更新"""
        # 設置房間的標準線分數，確保有分數計算
        self.room.standard_line_score = 10.0
        self.room.save()
        
        # 創建一條路線，並設置成員完成狀態
        route = self.factory.create_route(
            room=self.room,
            name="測試路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        
        # 設置成員1完成該路線
        score1 = Score.objects.get(route=route, member=self.m1)
        score1.is_completed = True
        score1.save()
        
        # 更新分數（觸發分數計算）
        from scoring.models import update_scores
        update_scores(self.room.id)
        
        # 獲取初始排行榜
        leaderboard_url = f'/api/rooms/{self.room.id}/leaderboard/'
        initial_response = self.client.get(leaderboard_url)
        self.assertEqual(initial_response.status_code, status.HTTP_200_OK)
        initial_leaderboard = initial_response.data.get('leaderboard', [])
        
        # 找到成員1的初始分數
        member1_initial = next((m for m in initial_leaderboard if m['id'] == self.m1.id), None)
        self.assertIsNotNone(member1_initial, "應該能找到成員1")
        initial_score = float(member1_initial['total_score'])
        
        # 驗證初始分數大於0（因為成員1完成了路線）
        self.assertGreater(initial_score, 0, f"成員1完成路線後應該有分數，實際: {initial_score}")
        
        # 刪除路線
        delete_url = f'/api/routes/{route.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 重新獲取排行榜，驗證分數已更新
        updated_response = self.client.get(leaderboard_url)
        self.assertEqual(updated_response.status_code, status.HTTP_200_OK)
        updated_leaderboard = updated_response.data.get('leaderboard', [])
        
        # 找到成員1的更新後分數
        member1_updated = next((m for m in updated_leaderboard if m['id'] == self.m1.id), None)
        self.assertIsNotNone(member1_updated, "應該能找到成員1")
        updated_score = float(member1_updated['total_score'])
        
        # 驗證分數已減少（因為路線被刪除，完成該路線的分數應該被移除）
        self.assertLessEqual(updated_score, initial_score, 
                       f"刪除路線後，成員1的分數應該減少或保持不變。初始: {initial_score}, 更新後: {updated_score}")
    
    def test_delete_route_removes_associated_scores(self):
        """測試：刪除路線後，相關的成績記錄也被刪除"""
        # 創建一條路線
        route = self.factory.create_route(
            room=self.room,
            name="測試路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        
        # 驗證初始狀態：應該有兩條成績記錄（每個成員一條）
        initial_scores = Score.objects.filter(route=route)
        self.assertEqual(initial_scores.count(), 2, "初始應該有兩條成績記錄")
        
        # 刪除路線
        delete_url = f'/api/routes/{route.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 驗證成績記錄已被刪除（由於外鍵 CASCADE，成績記錄應該被自動刪除）
        remaining_scores = Score.objects.filter(route=route)
        self.assertEqual(remaining_scores.count(), 0, "刪除路線後，相關的成績記錄應該也被刪除")
        
        # 驗證路線本身也被刪除
        route_exists = Route.objects.filter(id=route.id).exists()
        self.assertFalse(route_exists, "路線應該已被刪除")

