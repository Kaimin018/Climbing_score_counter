"""
手機照片上傳功能測試用例

測試手機可以通過以下方式上傳照片：
1. 拍照上傳（使用相機）
2. 從圖庫選擇照片上傳
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, cleanup_test_photos
from django.contrib.auth.models import User
from PIL import Image
from io import BytesIO
import json
import logging

logger = logging.getLogger(__name__)


class TestCaseMobilePhotoUpload(TestCase):
    """測試手機照片上傳功能（拍照和圖庫選擇）"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("手機照片上傳測試房間")
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
        
        # 創建測試圖片（模擬拍照）
        self.camera_image = self._create_test_image('camera', color='blue')
        
        # 創建測試圖片（模擬從圖庫選擇）
        self.gallery_image = self._create_test_image('gallery', color='green')
    
    def _create_test_image(self, name, color='red', size=(800, 600)):
        """創建測試圖片"""
        img = Image.new('RGB', size, color=color)
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return SimpleUploadedFile(
            name=f'{name}_photo.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
    
    def tearDown(self):
        """清理測試數據"""
        # 使用 cleanup_test_data 的 cleanup_photos 參數自動清理圖片
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def assert_photo_uploaded_correctly(self, response, route_id=None):
        """驗證照片是否正確上傳的輔助方法"""
        if route_id is None:
            route_id = response.data['id']
        
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在於存儲中: {route.photo.name}")
        self.assertTrue(route.photo.name.startswith('route_photos/'),
                      f"照片應該保存在 route_photos/ 目錄下，實際路徑: {route.photo.name}")
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        
        if default_storage.exists(route.photo.name):
            file_size = default_storage.size(route.photo.name)
            self.assertGreater(file_size, 0, 
                             f"照片文件大小應該大於 0，實際: {file_size} bytes")
        
        return route
    
    def test_create_route_with_camera_photo(self):
        """測試：通過拍照功能創建路線（模擬手機拍照）"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 模擬拍照上傳（使用 capture 屬性）
        data = {
            'name': '拍照路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.camera_image
        }
        
        # 模擬手機 User-Agent
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        logger.info(f"拍照上傳測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"拍照上傳應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證照片上傳
        self.assert_photo_uploaded_correctly(response)
    
    def test_create_route_with_gallery_photo(self):
        """測試：通過圖庫選擇功能創建路線（模擬從圖庫選擇）"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 模擬從圖庫選擇上傳（不使用 capture 屬性）
        data = {
            'name': '圖庫選擇路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.gallery_image
        }
        
        # 模擬手機 User-Agent
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        logger.info(f"圖庫選擇上傳測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"圖庫選擇上傳應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證照片上傳
        self.assert_photo_uploaded_correctly(response)
    
    def test_update_route_with_camera_photo(self):
        """測試：通過拍照功能更新路線照片"""
        # 先創建一個沒有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="原始路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        url = f'/api/routes/{route.id}/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        # 模擬拍照上傳
        data = {
            'name': '原始路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': self.camera_image
        }
        
        response = self.client.patch(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"拍照更新應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證照片上傳
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在: {route.photo.name}")
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
    
    def test_update_route_with_gallery_photo(self):
        """測試：通過圖庫選擇功能更新路線照片"""
        # 先創建一個沒有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="原始路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        url = f'/api/routes/{route.id}/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        # 模擬從圖庫選擇上傳
        data = {
            'name': '原始路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': self.gallery_image
        }
        
        response = self.client.patch(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"圖庫選擇更新應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證照片上傳
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在: {route.photo.name}")
        self.assertIn('photo_url', response.data)
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
    
    def test_camera_and_gallery_photo_different_sources(self):
        """測試：拍照和圖庫選擇的照片可以正確區分和上傳"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 先測試拍照上傳
        camera_data = {
            'name': '拍照路線1',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.camera_image
        }
        
        camera_response = self.client.post(
            url,
            data=camera_data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(camera_response.status_code, status.HTTP_201_CREATED)
        camera_route = self.assert_photo_uploaded_correctly(camera_response)
        
        # 再測試圖庫選擇上傳
        gallery_data = {
            'name': '圖庫選擇路線1',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.gallery_image
        }
        
        gallery_response = self.client.post(
            url,
            data=gallery_data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(gallery_response.status_code, status.HTTP_201_CREATED)
        gallery_route = self.assert_photo_uploaded_correctly(gallery_response)
        
        # 驗證兩個路線的照片不同
        self.assertNotEqual(camera_route.photo.name, gallery_route.photo.name,
                          "拍照和圖庫選擇的照片應該保存在不同的文件中")
        
        # 驗證兩個照片文件都存在
        self.assertTrue(default_storage.exists(camera_route.photo.name),
                      "拍照的照片文件應該存在")
        self.assertTrue(default_storage.exists(gallery_route.photo.name),
                      "圖庫選擇的照片文件應該存在")

