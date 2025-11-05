from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score, update_scores


class TestCaseRouteUpdateCompletions(TestCase):
    """測試案例：更新路線成員完成狀態"""

    def setUp(self):
        self.client = APIClient()
        self.room = Room.objects.create(name="測試房間")
        self.m1 = Member.objects.create(room=self.room, name="王小明", is_custom_calc=False)
        self.m2 = Member.objects.create(room=self.room, name="李大華", is_custom_calc=False)
        self.m3 = Member.objects.create(room=self.room, name="張三", is_custom_calc=False)
        self.m4 = Member.objects.create(room=self.room, name="陳四", is_custom_calc=False)
        
        # 創建測試路線
        self.route = Route.objects.create(room=self.room, name="【路線】路線1", grade="V3")
        
        # 創建成績記錄（初始狀態：所有人未完成）
        Score.objects.create(member=self.m1, route=self.route, is_completed=False)
        Score.objects.create(member=self.m2, route=self.route, is_completed=False)
        Score.objects.create(member=self.m3, route=self.route, is_completed=False)
        Score.objects.create(member=self.m4, route=self.route, is_completed=False)

    def test_update_route_mark_two_members_completed(self):
        """測試：更新路線，標記兩個成員為完成"""
        url = f'/api/routes/{self.route.id}/'
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): True,
                str(self.m2.id): True,
                str(self.m3.id): False,
                str(self.m4.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score3 = Score.objects.get(member=self.m3, route=self.route)
        score4 = Score.objects.get(member=self.m4, route=self.route)
        
        self.assertTrue(score1.is_completed, "M1 應該被標記為完成")
        self.assertTrue(score2.is_completed, "M2 應該被標記為完成")
        self.assertFalse(score3.is_completed, "M3 應該保持未完成")
        self.assertFalse(score4.is_completed, "M4 應該保持未完成")

    def test_update_route_unmark_completed_members(self):
        """測試：更新路線，取消已完成的成員"""
        # 先設置兩個成員為完成
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score1.is_completed = True
        score2.is_completed = True
        score1.save()
        score2.save()
        
        url = f'/api/routes/{self.route.id}/'
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): False,
                str(self.m2.id): False,
                str(self.m3.id): False,
                str(self.m4.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態
        score1.refresh_from_db()
        score2.refresh_from_db()
        self.assertFalse(score1.is_completed, "M1 應該被取消完成")
        self.assertFalse(score2.is_completed, "M2 應該被取消完成")

    def test_update_route_partial_member_completions(self):
        """測試：更新路線，只提供部分成員的完成狀態（其他應設為False）"""
        url = f'/api/routes/{self.route.id}/'
        # 只提供 M1 的完成狀態
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): True
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score3 = Score.objects.get(member=self.m3, route=self.route)
        score4 = Score.objects.get(member=self.m4, route=self.route)
        
        self.assertTrue(score1.is_completed, "M1 應該被標記為完成")
        # 其他成員應該設為 False（因為沒有在 member_completions 中提供）
        self.assertFalse(score2.is_completed, "M2 應該設為未完成")
        self.assertFalse(score3.is_completed, "M3 應該設為未完成")
        self.assertFalse(score4.is_completed, "M4 應該設為未完成")

    def test_update_route_with_empty_member_completions(self):
        """測試：更新路線，提供空的 member_completions（所有成員應設為False）"""
        # 先設置兩個成員為完成
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score1.is_completed = True
        score2.is_completed = True
        score1.save()
        score2.save()
        
        url = f'/api/routes/{self.route.id}/'
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': {}  # 空字典
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態：所有成員應該設為 False
        score1.refresh_from_db()
        score2.refresh_from_db()
        score3 = Score.objects.get(member=self.m3, route=self.route)
        score4 = Score.objects.get(member=self.m4, route=self.route)
        
        self.assertFalse(score1.is_completed, "M1 應該設為未完成")
        self.assertFalse(score2.is_completed, "M2 應該設為未完成")
        self.assertFalse(score3.is_completed, "M3 應該設為未完成")
        self.assertFalse(score4.is_completed, "M4 應該設為未完成")

    def test_update_route_with_json_string_member_completions(self):
        """測試：更新路線，使用 JSON 字符串格式的 member_completions"""
        import json
        url = f'/api/routes/{self.route.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)  # JSON 字符串
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        self.assertTrue(score1.is_completed, "M1 應該被標記為完成")
        self.assertTrue(score2.is_completed, "M2 應該被標記為完成")

    def test_update_route_verify_scores_updated(self):
        """測試：更新路線後，驗證分數計算是否正確"""
        url = f'/api/routes/{self.route.id}/'
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): True,
                str(self.m2.id): True
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 觸發計分更新
        update_scores(self.room.id)
        
        # 驗證分數
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 4個成員，L = LCM(1,2,3,4) = 12
        # 2人完成，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 6.00)
        self.assertEqual(float(self.m2.total_score), 6.00)

