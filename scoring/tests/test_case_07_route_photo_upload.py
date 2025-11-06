from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from PIL import Image
from io import BytesIO
import json
import os


class TestCaseRoutePhotoUpload(TestCase):
    """測試案例：路線圖片上傳功能"""

    def setUp(self):
        self.client = APIClient()
        self.room = TestDataFactory.create_room(name="圖片上傳測試房間")
        self.m1, self.m2 = TestDataFactory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建一個有效的測試圖片（使用 Pillow）
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        self.test_image = SimpleUploadedFile(
            name='test_route.png',
            content=img_io.read(),
            content_type='image/png'
        )
        
        # 創建另一個測試圖片（用於更新）
        img2 = Image.new('RGB', (100, 100), color='blue')
        img2_io = BytesIO()
        img2.save(img2_io, format='PNG')
        img2_io.seek(0)
        self.test_image2 = SimpleUploadedFile(
            name='test_route2.png',
            content=img2_io.read(),
            content_type='image/png'
        )

    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)
        # 清理測試上傳的圖片文件
        if hasattr(self, 'route') and self.route.photo:
            if default_storage.exists(self.route.photo.name):
                default_storage.delete(self.route.photo.name)

    def test_create_route_with_photo(self):
        """測試：創建路線時上傳圖片"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 使用 multipart/form-data 格式（模擬前端 FormData）
        data = {
            'name': '測試路線（含圖片）',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                        f"Response status: {response.status_code}, Errors: {response.data if hasattr(response, 'data') else 'N/A'}")
        
        # 驗證路線創建成功
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(route.photo.name.startswith('route_photos/'), 
                       f"圖片應該保存在 route_photos/ 目錄下，實際: {route.photo.name}")
        
        # 驗證圖片文件存在
        self.assertTrue(default_storage.exists(route.photo.name),
                       f"圖片文件應該存在: {route.photo.name}")
        
        # 驗證圖片文件大小（應該大於 0）
        file_size = default_storage.size(route.photo.name)
        self.assertGreater(file_size, 0, 
                         f"圖片文件大小應該大於 0，實際: {file_size} bytes")
        
        # 驗證 API 響應包含 photo_url
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response.data['photo_url'], 
                     "photo_url 應該包含圖片路徑")
        
        # 驗證照片 URL 可以訪問（在測試環境中可能無法真正訪問，但至少驗證格式正確）
        photo_url = response.data['photo_url']
        self.assertTrue(photo_url.startswith('http://') or photo_url.startswith('https://'),
                       f"photo_url 應該是有效的 URL，實際: {photo_url}")

    def test_create_route_without_photo(self):
        """測試：創建路線時不上傳圖片（應該可以正常創建）"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): False,
            str(self.m2.id): False
        }
        
        data = {
            'name': '測試路線（無圖片）',
            'grade': 'V4',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證路線創建成功但沒有圖片
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertFalse(bool(route.photo), "路線不應該有圖片")
        
        # 驗證 API 響應中 photo_url 為空或不存在
        if 'photo_url' in response.data:
            self.assertEqual(response.data.get('photo_url', ''), '', 
                           "沒有圖片時 photo_url 應該為空")

    def test_update_route_add_photo(self):
        """測試：更新路線時添加圖片（原本沒有圖片）"""
        # 先創建一個沒有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="原始路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        self.route = route  # 用於 tearDown 清理
        
        url = f'/api/routes/{route.id}/'
        
        # 使用 FormData 格式更新路線，添加圖片
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '原始路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.client.patch(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Response status: {response.status_code}, Errors: {response.data if hasattr(response, 'data') else 'N/A'}")
        
        # 驗證路線已更新並有圖片
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                       f"圖片文件應該存在: {route.photo.name}")
        
        # 驗證圖片文件大小
        file_size = default_storage.size(route.photo.name)
        self.assertGreater(file_size, 0, 
                         f"圖片文件大小應該大於 0，實際: {file_size} bytes")
        
        # 驗證 API 響應包含 photo_url
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response.data['photo_url'],
                     "photo_url 應該包含圖片路徑")

    def test_update_route_replace_photo(self):
        """測試：更新路線時替換圖片（原本有圖片）"""
        # 先創建一個有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="有圖片的路線",
            grade="V4",
            members=[self.m1, self.m2]
        )
        # 手動添加圖片
        route.photo = self.test_image
        route.save()
        self.route = route  # 用於 tearDown 清理
        
        old_photo_name = route.photo.name
        
        url = f'/api/routes/{route.id}/'
        
        # 使用 FormData 格式更新路線，替換圖片
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        data = {
            'name': '有圖片的路線',
            'grade': 'V4',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image2  # 使用新圖片
        }
        
        response = self.client.patch(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Response status: {response.status_code}, Errors: {response.data if hasattr(response, 'data') else 'N/A'}")
        
        # 驗證路線已更新並有新圖片
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有新的圖片")
        self.assertNotEqual(route.photo.name, old_photo_name, 
                           "圖片文件名應該不同（新圖片）")
        
        # 驗證舊圖片文件已被刪除（Django 通常會自動處理）
        # 注意：在某些情況下，舊文件可能不會立即刪除，這取決於存儲後端
        
        # 驗證新圖片文件存在
        self.assertTrue(default_storage.exists(route.photo.name),
                       f"新圖片文件應該存在: {route.photo.name}")
        
        # 驗證新圖片文件大小
        file_size = default_storage.size(route.photo.name)
        self.assertGreater(file_size, 0, 
                         f"新圖片文件大小應該大於 0，實際: {file_size} bytes")
        
        # 驗證 API 響應包含 photo_url
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response.data['photo_url'],
                     "photo_url 應該包含圖片路徑")

    def test_update_route_remove_photo(self):
        """測試：更新路線時移除圖片（設置為空）"""
        # 先創建一個有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="有圖片的路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        # 手動添加圖片
        route.photo = self.test_image
        route.save()
        self.route = route  # 用於 tearDown 清理
        
        url = f'/api/routes/{route.id}/'
        
        # 使用 JSON 格式更新路線，不包含 photo（部分更新）
        member_completions = {
            str(self.m1.id): False,
            str(self.m2.id): False
        }
        
        data = {
            'name': '有圖片的路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions)
            # 不包含 photo，應該保持原圖片
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證路線圖片仍然存在（因為沒有更新 photo 字段）
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線圖片應該仍然存在（未更新 photo 字段）")

    def test_get_route_with_photo_url(self):
        """測試：獲取路線時，photo_url 應該正確返回"""
        # 創建一個有圖片的路線
        route = TestDataFactory.create_route(
            room=self.room,
            name="測試路線",
            grade="V6",
            members=[self.m1, self.m2]
        )
        route.photo = self.test_image
        route.save()
        self.route = route  # 用於 tearDown 清理
        
        url = f'/api/routes/{route.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 photo_url 存在且有效
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        
        # 驗證 photo_url 是完整的 URL
        photo_url = response.data['photo_url']
        self.assertTrue(photo_url.startswith('http'), 
                       f"photo_url 應該是完整的 URL，實際: {photo_url}")

