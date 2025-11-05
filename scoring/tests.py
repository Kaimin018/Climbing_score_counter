from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Room, Member, Route, Score, update_scores
from decimal import Decimal


class ScoringLogicTestCase(TestCase):
    """測試核心計分邏輯"""

    def setUp(self):
        """設置測試數據"""
        self.room = Room.objects.create(name="測試房間", standard_line_score=12)
        self.m1 = Member.objects.create(room=self.room, name="王小明", is_custom_calc=False)
        self.m2 = Member.objects.create(room=self.room, name="李大華", is_custom_calc=False)
        self.m3 = Member.objects.create(room=self.room, name="張三", is_custom_calc=True)

    def test_case_1_to_10(self):
        """測試案例 1-10：循序漸進新增路線"""
        L = 12

        # 案例 1: R1 (Green V2) - M1, M3 完成
        r1 = Route.objects.create(room=self.room, name="R1", grade="Green V2")
        Score.objects.create(member=self.m1, route=r1, is_completed=True)
        Score.objects.create(member=self.m2, route=r1, is_completed=False)
        Score.objects.create(member=self.m3, route=r1, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 12.00)
        self.assertEqual(float(self.m3.total_score), 12.00)

        # 案例 2: R2 (Blue V4) - M2, M3 完成
        r2 = Route.objects.create(room=self.room, name="R2", grade="Blue V4")
        Score.objects.create(member=self.m1, route=r2, is_completed=False)
        Score.objects.create(member=self.m2, route=r2, is_completed=True)
        Score.objects.create(member=self.m3, route=r2, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 12.00)
        self.assertEqual(float(self.m2.total_score), 12.00)
        self.assertEqual(float(self.m3.total_score), 24.00)

        # 案例 3: R3 (Red V4) - M1, M2 完成
        r3 = Route.objects.create(room=self.room, name="R3", grade="Red V4")
        Score.objects.create(member=self.m1, route=r3, is_completed=True)
        Score.objects.create(member=self.m2, route=r3, is_completed=True)
        Score.objects.create(member=self.m3, route=r3, is_completed=False)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 18.00)  # 12 + 6
        self.assertEqual(float(self.m2.total_score), 18.00)  # 12 + 6

        # 案例 4: R4 (Yellow V6) - M1, M2 完成
        r4 = Route.objects.create(room=self.room, name="R4", grade="Yellow V6")
        Score.objects.create(member=self.m1, route=r4, is_completed=True)
        Score.objects.create(member=self.m2, route=r4, is_completed=True)
        Score.objects.create(member=self.m3, route=r4, is_completed=False)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 24.00)  # 12 + 6 + 6
        self.assertEqual(float(self.m2.total_score), 24.00)  # 12 + 6 + 6

        # 案例 5: R5 (Black V7) - 僅 M3 (客製化) 完成
        r5 = Route.objects.create(room=self.room, name="R5", grade="Black V7")
        Score.objects.create(member=self.m1, route=r5, is_completed=False)
        Score.objects.create(member=self.m2, route=r5, is_completed=False)
        Score.objects.create(member=self.m3, route=r5, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 24.00)
        self.assertEqual(float(self.m2.total_score), 24.00)
        self.assertEqual(float(self.m3.total_score), 36.00)  # 24 + 12

        # 案例 7: R7 (Pink V3) - M1, M2 完成
        r7 = Route.objects.create(room=self.room, name="R7", grade="Pink V3")
        Score.objects.create(member=self.m1, route=r7, is_completed=True)
        Score.objects.create(member=self.m2, route=r7, is_completed=True)
        Score.objects.create(member=self.m3, route=r7, is_completed=False)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 30.00)  # 24 + 6
        self.assertEqual(float(self.m2.total_score), 30.00)  # 24 + 6

        # 案例 8: R8 (Brown V8) - M2, M3 完成
        r8 = Route.objects.create(room=self.room, name="R8", grade="Brown V8")
        Score.objects.create(member=self.m1, route=r8, is_completed=False)
        Score.objects.create(member=self.m2, route=r8, is_completed=True)
        Score.objects.create(member=self.m3, route=r8, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 30.00)
        self.assertEqual(float(self.m2.total_score), 42.00)  # 30 + 12
        self.assertEqual(float(self.m3.total_score), 48.00)  # 36 + 12

        # 案例 9: R9 (Orange V5) - M1, M2, M3 完成
        r9 = Route.objects.create(room=self.room, name="R9", grade="Orange V5")
        Score.objects.create(member=self.m1, route=r9, is_completed=True)
        Score.objects.create(member=self.m2, route=r9, is_completed=True)
        Score.objects.create(member=self.m3, route=r9, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 36.00)  # 30 + 6
        self.assertEqual(float(self.m2.total_score), 48.00)  # 42 + 6
        self.assertEqual(float(self.m3.total_score), 60.00)  # 48 + 12

        # 案例 10: R10 (White V1) - M1, M3 完成
        r10 = Route.objects.create(room=self.room, name="R10", grade="White V1")
        Score.objects.create(member=self.m1, route=r10, is_completed=True)
        Score.objects.create(member=self.m2, route=r10, is_completed=False)
        Score.objects.create(member=self.m3, route=r10, is_completed=True)
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 48.00)  # 36 + 12
        self.assertEqual(float(self.m2.total_score), 48.00)
        self.assertEqual(float(self.m3.total_score), 72.00)  # 60 + 12

    def test_case_11_12_13(self):
        """測試案例 11-13：進階操作（取消完成、刪除路線）"""
        # 先建立案例 10 的狀態
        self.test_case_1_to_10()

        # 案例 11: M1 將 R10 標記為「未完成」
        r10 = Route.objects.get(name="R10")
        score_m1_r10 = Score.objects.get(member=self.m1, route=r10)
        score_m1_r10.is_completed = False
        score_m1_r10.save()
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 36.00)  # 48 - 12
        self.assertEqual(float(self.m2.total_score), 48.00)
        self.assertEqual(float(self.m3.total_score), 60.00)  # 72 - 12

        # 案例 12: 刪除路線 R3
        r3 = Route.objects.get(name="R3")
        r3.delete()  # 會級聯刪除相關的 Score
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 30.00)  # 36 - 6
        self.assertEqual(float(self.m2.total_score), 42.00)  # 48 - 6
        self.assertEqual(float(self.m3.total_score), 48.00)  # 60 - 12

        # 案例 13: M3 將 R5 標記為「未完成」
        r5 = Route.objects.get(name="R5")
        score_m3_r5 = Score.objects.get(member=self.m3, route=r5)
        score_m3_r5.is_completed = False
        score_m3_r5.save()
        update_scores(self.room.id)
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.assertEqual(float(self.m1.total_score), 30.00)
        self.assertEqual(float(self.m2.total_score), 42.00)
        self.assertEqual(float(self.m3.total_score), 36.00)  # 48 - 12


class APITestCase(TestCase):
    """測試 API 接口"""

    def setUp(self):
        self.client = APIClient()
        self.room = Room.objects.create(name="API測試房間", standard_line_score=12)
        self.m1 = Member.objects.create(room=self.room, name="測試成員1", is_custom_calc=False)
        self.m2 = Member.objects.create(room=self.room, name="測試成員2", is_custom_calc=False)

    def test_get_leaderboard(self):
        """測試獲取排行榜"""
        url = f'/api/rooms/{self.room.id}/leaderboard/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('room_info', response.data)
        self.assertIn('leaderboard', response.data)

    def test_create_route(self):
        """測試創建路線"""
        url = f'/api/rooms/{self.room.id}/routes/'
        data = {
            'name': '測試路線',
            'grade': 'V4',
            'photo_url': '',
            'member_completions': {
                str(self.m1.id): True,
                str(self.m2.id): False
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Route.objects.count(), 1)
        self.assertEqual(Score.objects.count(), 2)

    def test_update_score(self):
        """測試更新成績"""
        route = Route.objects.create(room=self.room, name="測試路線")
        score = Score.objects.create(member=self.m1, route=route, is_completed=False)
        
        url = f'/api/scores/{score.id}/'
        data = {'is_completed': True}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        score.refresh_from_db()
        self.assertTrue(score.is_completed)

