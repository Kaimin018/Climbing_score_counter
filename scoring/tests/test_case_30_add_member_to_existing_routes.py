"""
新增成員到現有路線測試用例

測試場景：
1. 創建房間，已有一些路線和成員
2. 新增成員A
3. 驗證新成員A自動為所有現有路線創建Score記錄（默認未完成）
4. 驗證新成員A在路線API響應中顯示
5. 驗證可以為新成員A設置完成狀態（打勾）
6. 驗證新成員A的完成狀態可以正確更新
7. 驗證更新路線時，新成員A顯示在路線選項中
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score, update_scores
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json


class TestCaseAddMemberToExistingRoutes(TestCase):
    """測試新增成員到現有路線的功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        
        # 創建測試用戶
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
        
        # 創建房間和初始成員
        self.room = self.factory.create_room("現有路線測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["成員1", "成員2"]
        )
        
        # 創建一些現有路線
        self.route1 = self.factory.create_route(
            room=self.room,
            name="路線1",
            grade="V3",
            members=[self.m1, self.m2],
            member_completions={self.m1.id: True, self.m2.id: False}
        )
        self.route2 = self.factory.create_route(
            room=self.room,
            name="路線2",
            grade="V4",
            members=[self.m1, self.m2],
            member_completions={self.m1.id: True, self.m2.id: True}
        )
        self.route3 = self.factory.create_route(
            room=self.room,
            name="路線3",
            grade="V5",
            members=[self.m1, self.m2],
            member_completions={self.m1.id: False, self.m2.id: False}
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def test_new_member_auto_creates_scores_for_existing_routes(self):
        """測試：新增成員A後，自動為所有現有路線創建Score記錄（默認未完成）"""
        # 驗證初始狀態：只有2個成員
        self.assertEqual(Member.objects.filter(room=self.room).count(), 2)
        
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member_a_id = response.data['id']
        member_a = Member.objects.get(id=member_a_id)
        
        # 驗證成員A已創建
        self.assertEqual(Member.objects.filter(room=self.room).count(), 3)
        
        # 驗證成員A為所有現有路線創建了Score記錄（默認未完成）
        scores = Score.objects.filter(member=member_a)
        self.assertEqual(scores.count(), 3, "成員A應該為3條路線創建Score記錄")
        
        for score in scores:
            self.assertFalse(score.is_completed, f"成員A在路線 {score.route.name} 應該默認未完成")
    
    def test_new_member_appears_in_route_api_response(self):
        """測試：新增成員A後，在路線API響應中顯示"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 獲取路線詳情
        route_url = f'/api/routes/{self.route1.id}/'
        route_response = self.client.get(route_url)
        self.assertEqual(route_response.status_code, status.HTTP_200_OK)
        
        # 驗證路線響應中包含成員A的Score記錄
        scores_data = route_response.data.get('scores', [])
        member_ids = [score['member_id'] for score in scores_data]
        self.assertIn(member_a_id, member_ids, "路線API響應應該包含成員A")
        
        # 找到成員A的Score數據
        member_a_score = next((s for s in scores_data if s['member_id'] == member_a_id), None)
        self.assertIsNotNone(member_a_score, "應該能找到成員A的Score數據")
        self.assertFalse(member_a_score['is_completed'], "成員A應該默認未完成")
        self.assertEqual(float(member_a_score['score_attained']), 0.00, "成員A的分數應該為0")
    
    def test_can_set_new_member_completion_status(self):
        """測試：可以為新成員A設置完成狀態（打勾）"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 更新路線1，設置成員A為完成
        route_url = f'/api/routes/{self.route1.id}/'
        update_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): False,
                str(member_a_id): True  # 設置成員A為完成
            })
        }
        update_response = self.client.patch(route_url, update_data, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # 驗證成員A的完成狀態已更新
        score_a = Score.objects.get(member_id=member_a_id, route=self.route1)
        self.assertTrue(score_a.is_completed, "成員A應該被標記為完成")
        
        # 驗證路線API響應中成員A的狀態
        route_response = self.client.get(route_url)
        scores_data = route_response.data.get('scores', [])
        member_a_score = next((s for s in scores_data if s['member_id'] == member_a_id), None)
        self.assertIsNotNone(member_a_score)
        self.assertTrue(member_a_score['is_completed'], "路線API響應中成員A應該顯示為完成")
    
    def test_can_update_new_member_completion_status(self):
        """測試：可以更新新成員A的完成狀態"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 第一次更新：設置成員A為完成
        route_url = f'/api/routes/{self.route1.id}/'
        update_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): False,
                str(member_a_id): True
            })
        }
        self.client.patch(route_url, update_data, format='json')
        
        # 驗證成員A已完成
        score_a = Score.objects.get(member_id=member_a_id, route=self.route1)
        self.assertTrue(score_a.is_completed)
        
        # 第二次更新：取消成員A的完成狀態
        update_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): False,
                str(member_a_id): False  # 取消完成
            })
        }
        self.client.patch(route_url, update_data, format='json')
        
        # 驗證成員A已取消完成
        score_a.refresh_from_db()
        self.assertFalse(score_a.is_completed, "成員A應該被取消完成狀態")
    
    def test_new_member_in_multiple_routes(self):
        """測試：新成員A在多條路線中都能正確顯示和設置"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 為多條路線設置成員A的完成狀態
        routes = [self.route1, self.route2, self.route3]
        completion_statuses = [True, True, False]  # 路線1和路線2完成，路線3未完成
        
        for route, is_completed in zip(routes, completion_statuses):
            route_url = f'/api/routes/{route.id}/'
            # 獲取當前所有成員的完成狀態
            current_route_response = self.client.get(route_url)
            current_scores = current_route_response.data.get('scores', [])
            
            # 構建member_completions，保持其他成員的狀態，更新成員A的狀態
            member_completions = {}
            for score_data in current_scores:
                member_id = score_data['member_id']
                member_completions[str(member_id)] = score_data['is_completed']
            member_completions[str(member_a_id)] = is_completed
            
            update_data = {
                'name': route.name,
                'grade': route.grade,
                'member_completions': json.dumps(member_completions)
            }
            update_response = self.client.patch(route_url, update_data, format='json')
            self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # 驗證成員A在各條路線中的完成狀態
        score1 = Score.objects.get(member_id=member_a_id, route=self.route1)
        score2 = Score.objects.get(member_id=member_a_id, route=self.route2)
        score3 = Score.objects.get(member_id=member_a_id, route=self.route3)
        
        self.assertTrue(score1.is_completed, "成員A在路線1應該完成")
        self.assertTrue(score2.is_completed, "成員A在路線2應該完成")
        self.assertFalse(score3.is_completed, "成員A在路線3應該未完成")
    
    def test_new_member_scores_calculated_correctly(self):
        """測試：新成員A完成路線後，分數計算正確"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        member_a = Member.objects.get(id=member_a_id)
        
        # 更新標準線分數（3個一般組成員，LCM(1,2,3) = 6）
        update_scores(self.room.id)
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 6)
        
        # 設置成員A完成路線1和路線2
        # 路線1：成員1完成，成員2未完成，成員A完成（2人完成）
        route1_url = f'/api/routes/{self.route1.id}/'
        update_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): False,
                str(member_a_id): True
            })
        }
        self.client.patch(route1_url, update_data, format='json')
        
        # 路線2：成員1完成，成員2完成，成員A完成（3人完成）
        route2_url = f'/api/routes/{self.route2.id}/'
        update_data = {
            'name': '路線2',
            'grade': 'V4',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): True,
                str(member_a_id): True
            })
        }
        self.client.patch(route2_url, update_data, format='json')
        
        # 更新分數
        update_scores(self.room.id)
        member_a.refresh_from_db()
        
        # 驗證成員A的分數
        # 路線1：L=6, 2人完成，每人得 6/2 = 3分
        # 路線2：L=6, 3人完成，每人得 6/3 = 2分
        # 成員A總分：3 + 2 = 5分
        self.assertEqual(float(member_a.total_score), 5.00, "成員A的總分應該是5分")
    
    def test_new_member_in_route_list_api(self):
        """測試：新成員A在路線列表API中顯示"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 獲取所有路線（通過RouteViewSet的list方法）
        # 注意：RouteViewSet可能沒有list方法，我們直接獲取每條路線的詳情
        routes = [self.route1, self.route2, self.route3]
        
        # 驗證每條路線的scores中都包含成員A
        for route in routes:
            route_url = f'/api/routes/{route.id}/'
            route_response = self.client.get(route_url)
            self.assertEqual(route_response.status_code, status.HTTP_200_OK)
            
            scores_data = route_response.data.get('scores', [])
            member_ids = [score['member_id'] for score in scores_data]
            self.assertIn(member_a_id, member_ids, 
                         f"路線 {route.name} 的scores中應該包含成員A")
    
    def test_new_member_after_route_update_still_appears(self):
        """測試：更新路線後，新成員A仍然顯示在路線選項中"""
        # 新增成員A
        url = '/api/members/'
        data = {
            'room': self.room.id,
            'name': '成員A',
            'is_custom_calc': False
        }
        response = self.client.post(url, data, format='json')
        member_a_id = response.data['id']
        
        # 更新路線1（不改變成員A的狀態）
        route_url = f'/api/routes/{self.route1.id}/'
        update_data = {
            'name': '路線1（更新）',
            'grade': 'V3',
            'member_completions': json.dumps({
                str(self.m1.id): True,
                str(self.m2.id): True,
                str(member_a_id): False
            })
        }
        update_response = self.client.patch(route_url, update_data, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # 驗證更新後，成員A仍然在路線響應中
        route_response = self.client.get(route_url)
        scores_data = route_response.data.get('scores', [])
        member_ids = [score['member_id'] for score in scores_data]
        self.assertIn(member_a_id, member_ids, "更新後成員A應該仍然在路線響應中")
        
        # 驗證成員A的狀態正確
        member_a_score = next((s for s in scores_data if s['member_id'] == member_a_id), None)
        self.assertIsNotNone(member_a_score)
        self.assertFalse(member_a_score['is_completed'], "成員A應該未完成")

