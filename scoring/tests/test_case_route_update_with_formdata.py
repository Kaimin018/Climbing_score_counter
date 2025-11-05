from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
import json


class TestCaseRouteUpdateWithFormData(TestCase):
    """測試案例：使用 FormData 更新路線（模擬前端實際場景）"""

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

    def test_update_route_with_formdata_mark_two_members(self):
        """測試：使用 FormData 格式（模擬前端）更新路線，標記兩個成員為完成"""
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        
        url = f'/api/routes/{self.route.id}/'
        
        # 模擬前端 FormData 的構建過程
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False,
            str(self.m4.id): False
        }
        
        # 構建 FormData（類似前端）
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)  # JSON 字符串，就像前端 FormData.append
        }
        
        # 使用 multipart/form-data 格式發送（模擬前端 FormData）
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"回應狀態碼: {response.status_code}, 錯誤: {response.data if hasattr(response, 'data') else 'N/A'}")
        
        # 驗證完成狀態
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score3 = Score.objects.get(member=self.m3, route=self.route)
        score4 = Score.objects.get(member=self.m4, route=self.route)
        
        self.assertTrue(score1.is_completed, f"M1 應該被標記為完成，但實際為: {score1.is_completed}")
        self.assertTrue(score2.is_completed, f"M2 應該被標記為完成，但實際為: {score2.is_completed}")
        self.assertFalse(score3.is_completed, f"M3 應該保持未完成，但實際為: {score3.is_completed}")
        self.assertFalse(score4.is_completed, f"M4 應該保持未完成，但實際為: {score4.is_completed}")

    def test_update_route_with_formdata_partial_checkboxes(self):
        """測試：使用 FormData，只勾選部分成員（未勾選的不在 FormData 中）"""
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        
        url = f'/api/routes/{self.route.id}/'
        
        # 模擬前端：只勾選了 M1 和 M2，未勾選的成員不會出現在 member_completions 中
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
            # M3 和 M4 沒有在字典中（未勾選）
        }
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證完成狀態
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score3 = Score.objects.get(member=self.m3, route=self.route)
        score4 = Score.objects.get(member=self.m4, route=self.route)
        
        self.assertTrue(score1.is_completed, "M1 應該被標記為完成")
        self.assertTrue(score2.is_completed, "M2 應該被標記為完成")
        # 未勾選的成員應該設為 False
        self.assertFalse(score3.is_completed, "M3 應該設為未完成（因為未在 member_completions 中）")
        self.assertFalse(score4.is_completed, "M4 應該設為未完成（因為未在 member_completions 中）")

    def test_update_route_with_formdata_empty_checkboxes(self):
        """測試：使用 FormData，所有成員都未勾選（member_completions 為空字典）"""
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        
        # 先設置兩個成員為完成
        score1 = Score.objects.get(member=self.m1, route=self.route)
        score2 = Score.objects.get(member=self.m2, route=self.route)
        score1.is_completed = True
        score2.is_completed = True
        score1.save()
        score2.save()
        
        url = f'/api/routes/{self.route.id}/'
        
        # 模擬前端：所有成員都未勾選，member_completions 為空字典
        member_completions = {}
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT
        )
        
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

    def test_update_route_verify_api_response(self):
        """測試：驗證 API 返回的數據中 scores 是否正確"""
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        
        url = f'/api/routes/{self.route.id}/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 API 返回的數據
        self.assertIn('scores', response.data, "API 回應應該包含 scores 字段")
        scores = response.data['scores']
        self.assertIsInstance(scores, list, "scores 應該是列表")
        
        # 統計完成人數
        completed_scores = [s for s in scores if s.get('is_completed', False)]
        self.assertEqual(len(completed_scores), 2, f"API 返回的完成人數應該是 2，但實際為: {len(completed_scores)}")
        
        # 驗證每個成員的完成狀態
        score_dict = {s['member_id']: s['is_completed'] for s in scores}
        self.assertTrue(score_dict.get(self.m1.id, False), f"M1 (ID={self.m1.id}) 在 API 回應中應該標記為完成")
        self.assertTrue(score_dict.get(self.m2.id, False), f"M2 (ID={self.m2.id}) 在 API 回應中應該標記為完成")
        self.assertFalse(score_dict.get(self.m3.id, True), f"M3 (ID={self.m3.id}) 在 API 回應中應該標記為未完成")
        self.assertFalse(score_dict.get(self.m4.id, True), f"M4 (ID={self.m4.id}) 在 API 回應中應該標記為未完成")

