from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.urls import reverse
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from PIL import Image
from io import BytesIO
import json


class TestCaseRoutePhotoThumbnail(TestCase):
    """測試案例：路線圖片縮圖顯示功能"""

    def setUp(self):
        self.client = APIClient()
        self.room = TestDataFactory.create_room(name="圖片縮圖測試房間")
        self.m1, self.m2 = TestDataFactory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試圖片
        img = Image.new('RGB', (200, 200), color='green')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        self.test_image = SimpleUploadedFile(
            name='test_route_thumbnail.png',
            content=img_io.read(),
            content_type='image/png'
        )

    def tearDown(self):
        """測試完成後清理數據"""
        # 使用 cleanup_test_data 的 cleanup_photos 參數自動清理圖片
        cleanup_test_data(room=self.room, cleanup_photos=True)

    def test_route_list_shows_photo_thumbnail(self):
        """測試：路線列表中有圖片的路線應該顯示縮圖"""
        # 創建一個有圖片的路線
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '有圖片的路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有圖片")
        
        # 獲取房間數據（模擬前端載入路線列表）
        room_url = f'/api/rooms/{self.room.id}/'
        room_response = self.client.get(room_url)
        
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        routes = room_response.data.get('routes', [])
        
        # 找到剛創建的路線
        created_route = next((r for r in routes if r['id'] == route_id), None)
        self.assertIsNotNone(created_route, "應該能找到創建的路線")
        
        # 驗證 photo_url 存在且不為空
        self.assertIn('photo_url', created_route)
        self.assertNotEqual(created_route['photo_url'], '', "photo_url 不應該為空")
        
        # 驗證 photo_url 是完整的 URL
        photo_url = created_route['photo_url']
        self.assertTrue(photo_url.startswith('http'), 
                       f"photo_url 應該是完整的 URL，實際: {photo_url}")
        
        # 照片會在 tearDown 中自動清理

    def test_route_list_no_thumbnail_for_route_without_photo(self):
        """測試：沒有圖片的路線不應該顯示縮圖"""
        # 創建一個沒有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="無圖片的路線",
            grade="V4",
            members=[self.m1, self.m2]
        )
        
        # 獲取房間數據（模擬前端載入路線列表）
        room_url = f'/api/rooms/{self.room.id}/'
        room_response = self.client.get(room_url)
        
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        routes = room_response.data.get('routes', [])
        
        # 找到剛創建的路線
        created_route = next((r for r in routes if r['id'] == route.id), None)
        self.assertIsNotNone(created_route, "應該能找到創建的路線")
        
        # 驗證 photo_url 為空或不存在
        if 'photo_url' in created_route:
            self.assertEqual(created_route.get('photo_url', ''), '', 
                           "沒有圖片時 photo_url 應該為空")

    def test_route_thumbnail_after_photo_update(self):
        """測試：更新路線圖片後，縮圖應該更新"""
        # 先創建一個沒有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="待更新圖片的路線",
            grade="V6",
            members=[self.m1, self.m2]
        )
        
        # 更新路線，添加圖片
        url = f'/api/routes/{route.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        data = {
            'name': '待更新圖片的路線',
            'grade': 'V6',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.client.patch(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證路線已更新並有圖片
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有圖片")
        
        # 獲取房間數據，驗證縮圖 URL 已更新
        room_url = f'/api/rooms/{self.room.id}/'
        room_response = self.client.get(room_url)
        
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        routes = room_response.data.get('routes', [])
        
        # 找到更新的路線
        updated_route = next((r for r in routes if r['id'] == route.id), None)
        self.assertIsNotNone(updated_route, "應該能找到更新的路線")
        
        # 驗證 photo_url 存在且不為空
        self.assertIn('photo_url', updated_route)
        self.assertNotEqual(updated_route['photo_url'], '', "photo_url 不應該為空")
        
        # 照片會在 tearDown 中自動清理

    def test_multiple_routes_with_and_without_photos(self):
        """測試：多個路線（有圖片和無圖片）同時存在時，縮圖顯示正確"""
        # 創建一個有圖片的路線
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True
        }
        
        data_with_photo = {
            'name': '有圖片的路線1',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response1 = self.client.post(url, data_with_photo, format='multipart')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        route1_id = response1.data['id']
        route1 = Route.objects.get(id=route1_id)
        
        # 創建一個沒有圖片的路線
        data_without_photo = {
            'name': '無圖片的路線2',
            'grade': 'V4',
            'member_completions': json.dumps(member_completions)
        }
        
        response2 = self.client.post(url, data_without_photo, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        route2_id = response2.data['id']
        
        # 獲取房間數據
        room_url = f'/api/rooms/{self.room.id}/'
        room_response = self.client.get(room_url)
        
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        routes = room_response.data.get('routes', [])
        
        # 驗證兩個路線都存在
        self.assertGreaterEqual(len(routes), 2, "應該至少有兩個路線")
        
        # 找到兩個路線
        route1_data = next((r for r in routes if r['id'] == route1_id), None)
        route2_data = next((r for r in routes if r['id'] == route2_id), None)
        
        self.assertIsNotNone(route1_data, "應該能找到有圖片的路線")
        self.assertIsNotNone(route2_data, "應該能找到無圖片的路線")
        
        # 驗證有圖片的路線有 photo_url
        self.assertIn('photo_url', route1_data)
        self.assertNotEqual(route1_data['photo_url'], '', "有圖片的路線 photo_url 不應該為空")
        
        # 驗證無圖片的路線 photo_url 為空
        if 'photo_url' in route2_data:
            self.assertEqual(route2_data.get('photo_url', ''), '', 
                           "無圖片的路線 photo_url 應該為空")
        
        # 清理
        if route1.photo and default_storage.exists(route1.photo.name):
            default_storage.delete(route1.photo.name)

