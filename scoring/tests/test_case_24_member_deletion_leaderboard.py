"""
成員刪除後排行榜更新測試用例

測試項目：
1. 刪除成員後，排行榜應該立即更新，移除該成員
2. 刪除成員後，成員列表應該更新
3. 刪除成員後，相關的成績記錄應該被刪除
4. 刪除成員後，其他成員的分數應該正確重新計算
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from scoring.models import update_scores
import json

logger = __import__('logging').getLogger(__name__)


class TestCaseMemberDeletionLeaderboard(TestCase):
    """測試成員刪除後排行榜更新"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("成員刪除測試房間")
        self.m1, self.m2, self.m3 = self.factory.create_normal_members(
            self.room,
            count=3,
            names=["成員1", "成員2", "成員3"]
        )
        
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
        
        # 設置成員1和成員2完成路線1
        score1 = Score.objects.get(route=self.route1, member=self.m1)
        score1.is_completed = True
        score1.save()
        
        score2 = Score.objects.get(route=self.route1, member=self.m2)
        score2.is_completed = True
        score2.save()
        
        # 更新分數
        update_scores(self.room.id)
        
        # 創建測試用戶
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def _get_leaderboard(self):
        """輔助方法：獲取排行榜數據"""
        url = f'/api/rooms/{self.room.id}/leaderboard/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data
    
    def test_delete_member_removes_from_leaderboard(self):
        """
        測試：刪除成員後，該成員應該從排行榜中移除
        
        測試步驟：
        1. 獲取初始排行榜，驗證包含成員1
        2. 刪除成員1
        3. 獲取更新後的排行榜，驗證成員1已不存在
        4. 驗證排行榜中只包含剩餘成員
        """
        # 獲取初始排行榜
        initial_data = self._get_leaderboard()
        initial_leaderboard = initial_data.get('leaderboard', [])
        
        # 驗證初始排行榜包含成員1
        initial_member_ids = [m['id'] for m in initial_leaderboard]
        self.assertIn(self.m1.id, initial_member_ids, "初始排行榜應該包含成員1")
        self.assertEqual(len(initial_leaderboard), 3, "初始應該有3個成員")
        
        # 刪除成員1
        delete_url = f'/api/members/{self.m1.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 獲取更新後的排行榜
        updated_data = self._get_leaderboard()
        updated_leaderboard = updated_data.get('leaderboard', [])
        
        # 驗證成員1已從排行榜中移除
        updated_member_ids = [m['id'] for m in updated_leaderboard]
        self.assertNotIn(self.m1.id, updated_member_ids, "刪除後，成員1應該從排行榜中移除")
        self.assertEqual(len(updated_leaderboard), 2, "刪除後應該只剩2個成員")
        
        # 驗證剩餘成員是成員2和成員3
        self.assertIn(self.m2.id, updated_member_ids, "應該包含成員2")
        self.assertIn(self.m3.id, updated_member_ids, "應該包含成員3")
    
    def test_delete_member_removes_associated_scores(self):
        """
        測試：刪除成員後，相關的成績記錄應該被刪除
        
        測試步驟：
        1. 驗證成員1有成績記錄
        2. 刪除成員1
        3. 驗證成員1的所有成績記錄已被刪除
        """
        # 驗證成員1有成績記錄
        initial_scores = Score.objects.filter(member=self.m1)
        self.assertGreater(initial_scores.count(), 0, "成員1應該有成績記錄")
        
        # 刪除成員1
        delete_url = f'/api/members/{self.m1.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 驗證成員1的所有成績記錄已被刪除
        remaining_scores = Score.objects.filter(member=self.m1)
        self.assertEqual(remaining_scores.count(), 0, "刪除成員後，相關成績記錄應該被刪除")
    
    def test_delete_member_updates_other_members_scores(self):
        """
        測試：刪除成員後，其他成員的分數應該正確重新計算
        
        測試步驟：
        1. 獲取初始排行榜，記錄成員2和成員3的分數
        2. 刪除成員1（成員1完成了路線1，會影響其他成員的分數）
        3. 獲取更新後的排行榜，驗證成員2和成員3的分數已更新
        """
        # 獲取初始排行榜
        initial_data = self._get_leaderboard()
        initial_leaderboard = initial_data.get('leaderboard', [])
        
        # 找到成員2和成員3的初始分數
        member2_initial = next((m for m in initial_leaderboard if m['id'] == self.m2.id), None)
        member3_initial = next((m for m in initial_leaderboard if m['id'] == self.m3.id), None)
        
        self.assertIsNotNone(member2_initial, "應該能找到成員2")
        self.assertIsNotNone(member3_initial, "應該能找到成員3")
        
        member2_initial_score = float(member2_initial['total_score'])
        member3_initial_score = float(member3_initial['total_score'])
        
        # 刪除成員1
        delete_url = f'/api/members/{self.m1.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 獲取更新後的排行榜
        updated_data = self._get_leaderboard()
        updated_leaderboard = updated_data.get('leaderboard', [])
        
        # 找到成員2和成員3的更新後分數
        member2_updated = next((m for m in updated_leaderboard if m['id'] == self.m2.id), None)
        member3_updated = next((m for m in updated_leaderboard if m['id'] == self.m3.id), None)
        
        self.assertIsNotNone(member2_updated, "應該能找到成員2")
        self.assertIsNotNone(member3_updated, "應該能找到成員3")
        
        member2_updated_score = float(member2_updated['total_score'])
        member3_updated_score = float(member3_updated['total_score'])
        
        # 驗證分數已更新（因為刪除了成員1，完成路線1的人數從2變為1，分數應該改變）
        # 注意：分數可能增加或減少，取決於實際的計算邏輯
        # 這裡我們主要驗證分數確實更新了（不是簡單的相等）
        self.assertNotEqual(member2_updated_score, member2_initial_score,
                          f"刪除成員1後，成員2的分數應該改變。初始: {member2_initial_score}, 更新後: {member2_updated_score}")
        
        # 成員3沒有完成路線，分數應該保持為0
        self.assertEqual(member3_updated_score, 0.0, "成員3沒有完成路線，分數應該為0")
    
    def test_delete_member_leaderboard_immediately_refreshes(self):
        """
        測試：刪除成員後，排行榜應該立即更新（模擬前端行為）
        
        測試步驟：
        1. 獲取初始排行榜
        2. 刪除成員
        3. 立即再次獲取排行榜（模擬前端刷新）
        4. 驗證排行榜已更新
        """
        # 獲取初始排行榜
        initial_data = self._get_leaderboard()
        initial_leaderboard = initial_data.get('leaderboard', [])
        initial_count = len(initial_leaderboard)
        
        # 刪除成員1
        delete_url = f'/api/members/{self.m1.id}/'
        delete_response = self.client.delete(delete_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 立即再次獲取排行榜（模擬前端立即刷新）
        updated_data = self._get_leaderboard()
        updated_leaderboard = updated_data.get('leaderboard', [])
        updated_count = len(updated_leaderboard)
        
        # 驗證排行榜已更新
        self.assertEqual(updated_count, initial_count - 1,
                        f"刪除成員後，排行榜成員數量應該減少1。初始: {initial_count}, 更新後: {updated_count}")
        
        # 驗證成員1已不存在
        updated_member_ids = [m['id'] for m in updated_leaderboard]
        self.assertNotIn(self.m1.id, updated_member_ids, "成員1應該已從排行榜中移除")
    
    def test_delete_last_member_leaderboard_empty(self):
        """
        測試：刪除所有成員後，排行榜應該為空
        
        測試步驟：
        1. 刪除所有成員
        2. 獲取排行榜
        3. 驗證排行榜為空
        """
        # 刪除所有成員
        for member in [self.m1, self.m2, self.m3]:
            delete_url = f'/api/members/{member.id}/'
            delete_response = self.client.delete(delete_url)
            self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 獲取排行榜
        data = self._get_leaderboard()
        leaderboard = data.get('leaderboard', [])
        
        # 驗證排行榜為空
        self.assertEqual(len(leaderboard), 0, "刪除所有成員後，排行榜應該為空")

