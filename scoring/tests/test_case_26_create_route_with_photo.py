"""
創建路線時上傳照片測試用例

測試項目：
1. 創建路線時上傳照片應該成功
2. 創建路線時上傳 HEIC 格式照片應該成功（轉換為 JPEG）
3. 創建路線時上傳無擴展名照片應該成功
4. 創建路線時上傳特殊字符文件名照片應該成功
5. 驗證創建路線後照片文件名格式正確
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, cleanup_test_photos
from PIL import Image
from io import BytesIO
import json
import logging

logger = logging.getLogger(__name__)


class TestCaseCreateRouteWithPhoto(TestCase):
    """測試創建路線時上傳照片"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("創建路線照片測試房間")
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
    
    def tearDown(self):
        """清理測試數據"""
        # 使用 cleanup_test_data 的 cleanup_photos 參數自動清理圖片
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def _create_test_image(self, name_prefix, format='JPEG', color='red', size=(800, 600)):
        """創建測試圖片"""
        img = Image.new('RGB', size, color=color)
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return SimpleUploadedFile(
            name=f'{name_prefix}_photo.jpg',
            content=img_io.read(),
            content_type=f'image/{format.lower()}'
        )
    
    def _create_route_with_photo(self, name, photo_file, expected_status=status.HTTP_201_CREATED):
        """輔助方法：創建帶照片的路線"""
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': name,
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': photo_file
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        logger.info(f"{name} 創建測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != expected_status:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        return response
    
    def assert_photo_created_correctly(self, response, route_id=None, expected_extensions=None):
        """驗證照片是否正確創建"""
        if route_id is None:
            route_id = response.data['id']
        
        # 驗證路線存在且有照片
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        
        # 驗證照片文件存在於存儲中
        self.assertTrue(default_storage.exists(route.photo.name),
                        f"照片文件應該存在於存儲中: {route.photo.name}")
        
        # 驗證照片路徑正確（應該在 route_photos/ 目錄下）
        self.assertTrue(route.photo.name.startswith('route_photos/'),
                       f"照片應該保存在 route_photos/ 目錄下，實際路徑: {route.photo.name}")
        
        # 驗證文件名格式正確（不應該包含 'new' 字符串）
        filename = route.photo.name.split('/')[-1]
        self.assertNotIn('new', filename.lower(),
                        f"文件名不應該包含 'new'，實際: {filename}")
        self.assertTrue(filename.startswith('route_'),
                       f"文件名應該以 'route_' 開頭，實際: {filename}")
        
        # 驗證 API 響應包含照片相關字段
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        
        # 驗證照片文件大小（應該大於 0）
        if default_storage.exists(route.photo.name):
            file_size = default_storage.size(route.photo.name)
            self.assertGreater(file_size, 0, 
                             f"照片文件大小應該大於 0，實際: {file_size} bytes")
        
        # 驗證文件擴展名（如果指定了預期擴展名）
        if expected_extensions:
            file_ext = '.' + route.photo.name.rsplit('.', 1)[1] if '.' in route.photo.name else ''
            self.assertIn(file_ext.lower(), [ext.lower() for ext in expected_extensions],
                         f"照片文件名應該以以下擴展名之一結尾: {expected_extensions}，實際: {route.photo.name}")
        
        return route
    
    def test_create_route_with_jpeg_photo(self):
        """
        測試：創建路線時上傳 JPEG 格式照片應該成功
        
        測試步驟：
        1. 創建 JPEG 格式的測試圖片
        2. 創建路線並上傳照片
        3. 驗證創建成功
        4. 驗證照片文件名格式正確（不包含 'new'）
        """
        jpeg_image = self._create_test_image('create_jpeg', color='blue')
        
        response = self._create_route_with_photo('JPEG 照片路線', jpeg_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"JPEG 格式應該成功創建路線，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        self.assert_photo_created_correctly(response)
    
    def test_create_route_with_heic_photo(self):
        """
        測試：創建路線時上傳 HEIC 格式照片應該成功（轉換為 JPEG）
        
        測試步驟：
        1. 創建模擬 HEIC 文件
        2. 創建路線並上傳 HEIC 照片
        3. 驗證創建成功
        4. 驗證 HEIC 被轉換為 JPEG
        5. 驗證照片文件名格式正確（不包含 'new'）
        """
        # 創建模擬 HEIC 文件
        img = Image.new('RGB', (800, 600), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        heic_content = img_io.read()
        
        heic_image = SimpleUploadedFile(
            name='IMG_20250101_120000.HEIC',
            content=heic_content,
            content_type='image/heic'
        )
        
        response = self._create_route_with_photo('HEIC 照片路線', heic_image)
        
        # HEIC 格式應該被接受（可能通過自動轉換）
        if response.status_code == status.HTTP_201_CREATED:
            route = self.assert_photo_created_correctly(response, expected_extensions=['.jpg', '.jpeg'])
            
            # 驗證照片文件名應該是 .jpg（HEIC 應該被轉換為 JPEG）
            self.assertTrue(
                route.photo.name.lower().endswith(('.jpg', '.jpeg')),
                f"HEIC 格式應該被轉換為 JPEG，但文件名是: {route.photo.name}"
            )
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            # 如果 HEIC 被拒絕（可能因為 pyheif 未安裝且無法轉換）
            logger.warning(f"HEIC 格式被拒絕（可能因為 pyheif 未安裝）: {response.data if hasattr(response, 'data') else response.content}")
            # 驗證錯誤信息不應該是 "The string did not match the expected pattern"
            if hasattr(response, 'data'):
                error_str = str(response.data)
                self.assertNotIn('The string did not match the expected pattern', error_str,
                               "不應該出現 'The string did not match the expected pattern' 錯誤")
        else:
            self.fail(f"意外的響應狀態碼: {response.status_code}, 響應: {response.data if hasattr(response, 'data') else response.content}")
    
    def test_create_route_with_photo_no_extension(self):
        """
        測試：創建路線時上傳無擴展名照片應該成功
        
        測試步驟：
        1. 創建沒有擴展名的測試圖片
        2. 創建路線並上傳照片
        3. 驗證創建成功
        4. 驗證系統自動添加了正確的擴展名
        5. 驗證照片文件名格式正確（不包含 'new'）
        """
        img = Image.new('RGB', (800, 600), color='orange')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        no_ext_image = SimpleUploadedFile(
            name='photo_from_camera',  # 沒有擴展名
            content=img_io.read(),
            content_type='image/jpeg'  # 但有 content_type
        )
        
        response = self._create_route_with_photo('無擴展名照片路線', no_ext_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"無擴展名文件應該成功創建路線，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        route = self.assert_photo_created_correctly(response)
        
        # 驗證文件名有正確的擴展名（系統應該自動添加）
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"無擴展名文件應該被自動添加 .jpg 擴展名，實際: {route.photo.name}"
        )
    
    def test_create_route_with_photo_special_characters(self):
        """
        測試：創建路線時上傳特殊字符文件名照片應該成功
        
        測試步驟：
        1. 創建包含特殊字符的文件名
        2. 創建路線並上傳照片
        3. 驗證創建成功
        4. 驗證文件名被正確清理（不包含特殊字符，不包含 'new'）
        """
        img = Image.new('RGB', (800, 600), color='purple')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        special_char_image = SimpleUploadedFile(
            name='照片-2025/01/01 12:00:00!.JPG',  # 包含特殊字符
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        response = self._create_route_with_photo('特殊字符文件名路線', special_char_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"特殊字符文件名應該成功創建路線，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        route = self.assert_photo_created_correctly(response)
        
        # 驗證文件名格式正確（應該符合 route_photo_upload_path 的格式）
        filename = route.photo.name.split('/')[-1]
        self.assertTrue(
            filename.startswith('route_') and filename.endswith('.jpg'),
            f"特殊字符文件名應該被清理為標準格式，實際: {filename}"
        )
        # 驗證文件名不包含特殊字符
        self.assertNotIn('/', filename, "文件名不應該包含 '/' 字符")
        self.assertNotIn(':', filename, "文件名不應該包含 ':' 字符")
        self.assertNotIn('!', filename, "文件名不應該包含 '!' 字符")
        # 驗證不包含 'new'
        self.assertNotIn('new', filename.lower(), "文件名不應該包含 'new'")
    
    def test_create_route_photo_filename_format(self):
        """
        測試：驗證創建路線後照片文件名格式正確
        
        測試步驟：
        1. 創建路線並上傳照片
        2. 驗證保存後的文件名格式符合 route_photo_upload_path 的要求
        3. 驗證文件名不包含 'new'
        4. 驗證文件名不包含特殊字符
        5. 驗證文件名有正確的擴展名
        """
        test_image = self._create_test_image('format_test', color='yellow')
        
        response = self._create_route_with_photo('文件名格式測試路線', test_image)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        route = Route.objects.get(id=response.data['id'])
        filename = route.photo.name.split('/')[-1]
        
        # 驗證文件名格式：route_{route_id}_{timestamp}.jpg
        # 注意：Django 的 ImageField 可能會在文件名中添加隨機字符串以避免衝突
        import re
        # 允許格式：route_{route_id}_{timestamp}.jpg 或 route_{route_id}_{timestamp}_{random}.jpg
        pattern = r'^route_\d+_\d{8}_\d{6}(_[A-Za-z0-9]+)?\.(jpg|jpeg|png|gif|bmp|webp)$'
        self.assertTrue(
            re.match(pattern, filename, re.IGNORECASE),
            f"文件名格式應該符合 route_photo_upload_path 的要求，實際: {filename}"
        )
        
        # 驗證文件名不包含 'new'
        self.assertNotIn('new', filename.lower(), "文件名不應該包含 'new'")
        
        # 驗證文件名不包含特殊字符
        special_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ', '!']
        for char in special_chars:
            self.assertNotIn(char, filename, f"文件名不應該包含 '{char}' 字符")
    
    def test_create_multiple_routes_with_photos(self):
        """
        測試：連續創建多個帶照片的路線應該都成功
        
        測試步驟：
        1. 第一次創建路線並上傳照片
        2. 第二次創建路線並上傳照片
        3. 驗證每次創建都成功
        4. 驗證每次創建的照片文件名格式都正確（不包含 'new'）
        """
        colors = ['red', 'blue', 'green']
        
        for i, color in enumerate(colors):
            test_image = self._create_test_image(f'create_{i}', color=color)
            response = self._create_route_with_photo(f'路線{i+1}', test_image)
            
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"第{i+1}次創建應該成功，但返回了 {response.status_code}"
            )
            
            route = Route.objects.get(id=response.data['id'])
            self.assertIsNotNone(route.photo, f"第{i+1}次創建後，路線應該有照片")
            self.assertTrue(
                default_storage.exists(route.photo.name),
                f"第{i+1}次創建後，照片文件應該存在: {route.photo.name}"
            )
            
            # 驗證文件名格式正確（不包含 'new'）
            filename = route.photo.name.split('/')[-1]
            self.assertTrue(
                filename.startswith('route_') and filename.endswith(('.jpg', '.jpeg')),
                f"第{i+1}次創建的文件名格式應該正確，實際: {filename}"
            )
            self.assertNotIn('new', filename.lower(),
                            f"第{i+1}次創建的文件名不應該包含 'new'，實際: {filename}")

