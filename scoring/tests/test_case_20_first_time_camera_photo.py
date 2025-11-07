"""
第一次選擇手機拍照格式問題測試用例

測試項目：
1. 第一次選擇手機拍照時，照片應該能正確顯示
2. 先選擇圖庫再選擇拍照，應該能正常顯示
3. 直接選擇拍照，應該能正常顯示（修復後的預期行為）
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from PIL import Image
from io import BytesIO
import json
import logging

logger = logging.getLogger(__name__)


class TestCaseFirstTimeCameraPhoto(TestCase):
    """測試第一次選擇手機拍照的格式問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("第一次拍照測試房間")
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
    
    def _create_test_image(self, name, color='red', size=(800, 600)):
        """創建測試圖片"""
        img = Image.new('RGB', size, color=color)
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return SimpleUploadedFile(
            name=f'{name}.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
        # 清理測試上傳的圖片文件
        routes = Route.objects.filter(room=self.room)
        for route in routes:
            if route.photo and default_storage.exists(route.photo.name):
                default_storage.delete(route.photo.name)
    
    def test_first_time_camera_photo_upload(self):
        """測試：第一次選擇手機拍照時，照片應該能正確上傳和顯示"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 模擬第一次選擇拍照（使用 JPEG 格式，模擬手機拍照）
        camera_image = self._create_test_image('camera_first', color='blue')
        
        data = {
            'name': '第一次拍照路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': camera_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"第一次拍照上傳應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證 API 響應包含照片相關字段
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
        
        # 驗證 photo_url 不為空且格式正確
        photo_url = response.data['photo_url']
        self.assertNotEqual(photo_url, '', "photo_url 不應該為空")
        self.assertTrue(
            photo_url.startswith('http://') or photo_url.startswith('https://') or photo_url.startswith('/media/'),
            f"photo_url 應該是有效的 URL 或路徑，實際: {photo_url}"
        )
        
        # 驗證數據庫中的路線有照片
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在: {route.photo.name}")
        
        # 驗證照片文件大小（應該大於 0）
        file_size = default_storage.size(route.photo.name)
        self.assertGreater(file_size, 0, 
                          f"照片文件大小應該大於 0，實際: {file_size} bytes")
    
    def test_gallery_then_camera_photo_upload(self):
        """測試：先選擇圖庫再選擇拍照，應該能正常顯示"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 先上傳一張圖庫照片
        gallery_image = self._create_test_image('gallery_first', color='green')
        data1 = {
            'name': '圖庫照片路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': gallery_image
        }
        
        response1 = self.client.post(url, data=data1, format='multipart')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED, "圖庫照片應該成功上傳")
        
        # 然後上傳一張拍照照片（模擬先選擇圖庫再選擇拍照的情況）
        camera_image = self._create_test_image('camera_after_gallery', color='purple')
        data2 = {
            'name': '拍照照片路線',
            'grade': 'V4',
            'member_completions': json.dumps(member_completions),
            'photo': camera_image
        }
        
        response2 = self.client.post(url, data=data2, format='multipart')
        self.assertEqual(
            response2.status_code,
            status.HTTP_201_CREATED,
            f"拍照照片應該成功上傳，但返回了 {response2.status_code}。錯誤: {response2.data if hasattr(response2, 'data') else response2.content}"
        )
        
        # 驗證兩張照片都正確上傳
        self.assertIn('photo_url', response1.data, "圖庫照片應該有 photo_url")
        self.assertIn('photo_url', response2.data, "拍照照片應該有 photo_url")
        
        route1 = Route.objects.get(id=response1.data['id'])
        route2 = Route.objects.get(id=response2.data['id'])
        
        self.assertIsNotNone(route1.photo, "圖庫照片路線應該有照片")
        self.assertIsNotNone(route2.photo, "拍照照片路線應該有照片")
        self.assertTrue(default_storage.exists(route1.photo.name), "圖庫照片文件應該存在")
        self.assertTrue(default_storage.exists(route2.photo.name), "拍照照片文件應該存在")
    
    def test_multiple_camera_photos_in_sequence(self):
        """測試：連續多次選擇拍照，每次都應該能正常顯示"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 連續上傳三張拍照照片
        for i in range(3):
            camera_image = self._create_test_image(f'camera_seq_{i}', color=['red', 'blue', 'green'][i])
            data = {
                'name': f'連續拍照路線{i+1}',
                'grade': f'V{i+3}',
                'member_completions': json.dumps(member_completions),
                'photo': camera_image
            }
            
            response = self.client.post(
                url,
                data=data,
                format='multipart',
                HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
            )
            
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"第{i+1}次拍照上傳應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
            )
            
            # 驗證每次上傳都有照片
            self.assertIn('photo_url', response.data, f"第{i+1}次拍照應該有 photo_url")
            photo_url = response.data['photo_url']
            self.assertNotEqual(photo_url, '', f"第{i+1}次拍照的 photo_url 不應該為空")
            
            # 驗證數據庫中的路線有照片
            route = Route.objects.get(id=response.data['id'])
            self.assertIsNotNone(route.photo, f"第{i+1}次拍照路線應該有照片")
            self.assertTrue(default_storage.exists(route.photo.name),
                          f"第{i+1}次拍照文件應該存在: {route.photo.name}")
    
    def test_camera_photo_with_special_filename(self):
        """測試：拍照時文件名包含特殊字符，應該能正確處理"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        # 創建模擬特殊文件名的照片（模擬手機拍照可能產生的文件名）
        special_image = SimpleUploadedFile(
            name='IMG_20250101_120000.jpg',  # 模擬 iPhone 拍照文件名
            content=self._create_test_image('special', color='orange').read(),
            content_type='image/jpeg'
        )
        
        data = {
            'name': '特殊文件名路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': special_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"特殊文件名拍照應該成功上傳，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證照片正確上傳
        self.assertIn('photo_url', response.data, "特殊文件名拍照應該有 photo_url")
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route.photo, "特殊文件名路線應該有照片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"特殊文件名照片文件應該存在: {route.photo.name}")

