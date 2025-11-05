from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score


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

    def test_create_room_add_member_create_route(self):
        """測試完整流程：創建新房間 -> 新增成員 -> 建立新路線"""
        # 步驟 1: 創建新房間
        room_data = {
            'name': '測試房間_20250101'
        }
        response = self.client.post('/api/rooms/', room_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        room_id = response.data['id']
        
        # 驗證房間創建成功
        self.assertEqual(Room.objects.count(), 2)  # 原有1個 + 新建1個
        self.assertEqual(response.data['name'], '測試房間_20250101')
        # 驗證每一條線總分預設為1（因為還沒有一般組成員）
        self.assertEqual(response.data['standard_line_score'], 1)
        
        # 步驟 2: 在該房間新增成員
        member1_data = {
            'room': room_id,
            'name': '測試成員A',
            'is_custom_calc': False
        }
        response = self.client.post('/api/members/', member1_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member1_id = response.data['id']
        
        member2_data = {
            'room': room_id,
            'name': '測試成員B',
            'is_custom_calc': False
        }
        response = self.client.post('/api/members/', member2_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member2_id = response.data['id']
        
        # 驗證成員創建成功
        self.assertEqual(Member.objects.filter(room_id=room_id).count(), 2)
        
        # 驗證每一條線總分自動更新（2個一般組成員，LCM(1,2) = 2）
        room = Room.objects.get(id=room_id)
        room.refresh_from_db()
        self.assertEqual(room.standard_line_score, 2)
        
        # 步驟 3: 建立新路線
        route_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': {
                str(member1_id): True,
                str(member2_id): False
            }
        }
        response = self.client.post(f'/api/rooms/{room_id}/routes/', route_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route_id = response.data['id']
        
        # 驗證路線創建成功
        self.assertEqual(Route.objects.filter(room_id=room_id).count(), 1)
        # 注意：API 返回的路線名稱不會自動加上【路線】前綴（這是前端處理的）
        # 但路線名稱應該正確保存
        self.assertEqual(response.data['name'], '路線1')
        
        # 驗證成績記錄創建成功
        self.assertEqual(Score.objects.filter(route_id=route_id).count(), 2)
        
        # 驗證完成狀態正確
        score1 = Score.objects.get(member_id=member1_id, route_id=route_id)
        score2 = Score.objects.get(member_id=member2_id, route_id=route_id)
        self.assertTrue(score1.is_completed)
        self.assertFalse(score2.is_completed)
        
        # 驗證分數計算正確（L=2, 1人完成，每人獲得2分）
        member1 = Member.objects.get(id=member1_id)
        member1.refresh_from_db()
        self.assertEqual(float(member1.total_score), 2.00)
        
        member2 = Member.objects.get(id=member2_id)
        member2.refresh_from_db()
        self.assertEqual(float(member2.total_score), 0.00)

