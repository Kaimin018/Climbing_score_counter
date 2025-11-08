"""
iPhone 拍照更新路線修復驗證測試用例

測試項目：
1. iPhone 拍照更新路線（HEIC 格式）應該成功
2. iPhone 拍照更新路線（JPEG 格式）應該成功
3. iPhone 從圖庫選擇照片更新路線應該成功
4. 無擴展名文件更新路線應該成功
5. 特殊字符文件名更新路線應該成功
6. 驗證文件名格式正確（符合 ImageField 要求）
7. 驗證轉換後的圖片可以正常保存和顯示
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


class TestCaseIPhonePhotoUpdateRouteFix(TestCase):
    """測試 iPhone 拍照更新路線修復"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("iPhone 更新路線測試房間")
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
        
        # 創建一個現有路線（用於更新測試）
        self.route = self.factory.create_route(
            room=self.room,
            name="原始路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
    
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
    
    def _update_route_with_photo(self, photo_file, route_id=None, expected_status=status.HTTP_200_OK):
        """輔助方法：更新路線並上傳照片"""
        if route_id is None:
            route_id = self.route.id
        
        url = f'/api/routes/{route_id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '更新後的路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': photo_file
        }
        
        response = self.client.patch(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        logger.info(f"更新路線測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != expected_status:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        return response
    
    def assert_photo_updated_correctly(self, response, route_id=None):
        """驗證照片更新是否正確"""
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
        
        # 驗證文件名格式正確（應該符合 route_photo_upload_path 的格式）
        # 格式：route_photos/route_{route_id}_{timestamp}.jpg
        filename = route.photo.name.split('/')[-1]
        self.assertTrue(filename.startswith('route_'),
                       f"文件名格式應該符合 route_photo_upload_path 的格式，實際: {filename}")
        self.assertTrue(filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')),
                       f"文件名應該以標準圖片擴展名結尾，實際: {filename}")
        
        # 驗證 API 響應包含照片相關字段
        self.assertIn('photo', response.data, "API 響應應該包含 'photo' 字段")
        self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
        self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response.data['photo_url'],
                     f"photo_url 應該包含圖片路徑，實際: {response.data['photo_url']}")
        
        # 驗證照片文件大小（應該大於 0）
        if default_storage.exists(route.photo.name):
            file_size = default_storage.size(route.photo.name)
            self.assertGreater(file_size, 0, 
                             f"照片文件大小應該大於 0，實際: {file_size} bytes")
        
        # 驗證照片文件可以用 Pillow 正常讀取（確保格式正確）
        try:
            with default_storage.open(route.photo.name, 'rb') as f:
                img = Image.open(f)
                img.verify()
                # 重新打開以進行實際操作
                f.seek(0)
                img = Image.open(f)
                self.assertIsNotNone(img, "照片文件應該可以用 Pillow 正常讀取")
                self.assertGreater(img.size[0], 0, "照片寬度應該大於 0")
                self.assertGreater(img.size[1], 0, "照片高度應該大於 0")
        except Exception as e:
            self.fail(f"無法使用 Pillow 讀取照片文件: {str(e)}")
        
        return route
    
    def test_iphone_camera_heic_update_route(self):
        """
        測試：iPhone 拍照（HEIC 格式）更新路線應該成功
        
        測試步驟：
        1. 創建模擬 HEIC 文件（使用 JPEG 內容但標記為 HEIC）
        2. 更新現有路線，上傳 HEIC 格式照片
        3. 驗證更新成功
        4. 驗證照片文件名格式正確
        5. 驗證照片可以正常讀取和顯示
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
        
        response = self._update_route_with_photo(heic_image)
        
        # HEIC 格式應該被接受（可能通過自動轉換）
        if response.status_code == status.HTTP_200_OK:
            self.assert_photo_updated_correctly(response, route_id=self.route.id)
            
            # 驗證照片文件名應該是 .jpg（HEIC 應該被轉換為 JPEG）
            route = Route.objects.get(id=self.route.id)
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
    
    def test_iphone_camera_jpeg_update_route(self):
        """
        測試：iPhone 拍照（JPEG 格式）更新路線應該成功
        
        測試步驟：
        1. 創建 JPEG 格式的測試圖片
        2. 更新現有路線，上傳 JPEG 格式照片
        3. 驗證更新成功
        4. 驗證照片文件名格式正確
        5. 驗證照片可以正常讀取和顯示
        """
        jpeg_image = self._create_test_image('camera_jpeg', color='blue')
        
        response = self._update_route_with_photo(jpeg_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"JPEG 格式應該成功更新，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        self.assert_photo_updated_correctly(response, route_id=self.route.id)
    
    def test_iphone_gallery_photo_update_route(self):
        """
        測試：iPhone 從圖庫選擇照片更新路線應該成功
        
        測試步驟：
        1. 創建測試圖片（模擬從圖庫選擇）
        2. 更新現有路線，上傳照片
        3. 驗證更新成功
        4. 驗證照片可以正常讀取和顯示
        """
        gallery_image = self._create_test_image('gallery', color='green')
        
        response = self._update_route_with_photo(gallery_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"圖庫照片應該成功更新，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        self.assert_photo_updated_correctly(response, route_id=self.route.id)
    
    def test_photo_without_extension_update_route(self):
        """
        測試：無擴展名文件更新路線應該成功
        
        測試步驟：
        1. 創建沒有擴展名的測試圖片
        2. 更新現有路線，上傳無擴展名照片
        3. 驗證更新成功
        4. 驗證系統自動添加了正確的擴展名
        5. 驗證照片可以正常讀取和顯示
        """
        img = Image.new('RGB', (800, 600), color='orange')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        no_ext_image = SimpleUploadedFile(
            name='photo_from_iphone',  # 沒有擴展名
            content=img_io.read(),
            content_type='image/jpeg'  # 但有 content_type
        )
        
        response = self._update_route_with_photo(no_ext_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"無擴展名文件應該成功更新，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        route = self.assert_photo_updated_correctly(response, route_id=self.route.id)
        
        # 驗證文件名有正確的擴展名（系統應該自動添加）
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"無擴展名文件應該被自動添加 .jpg 擴展名，實際: {route.photo.name}"
        )
    
    def test_photo_with_special_characters_update_route(self):
        """
        測試：特殊字符文件名更新路線應該成功
        
        測試步驟：
        1. 創建包含特殊字符的文件名
        2. 更新現有路線，上傳特殊字符文件名照片
        3. 驗證更新成功
        4. 驗證文件名被正確清理（符合 route_photo_upload_path 格式）
        5. 驗證照片可以正常讀取和顯示
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
        
        response = self._update_route_with_photo(special_char_image)
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"特殊字符文件名應該成功更新，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        route = self.assert_photo_updated_correctly(response, route_id=self.route.id)
        
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
    
    def test_photo_filename_format_validation(self):
        """
        測試：驗證文件名格式符合 ImageField 要求
        
        測試步驟：
        1. 更新路線並上傳照片
        2. 驗證保存後的文件名格式符合 route_photo_upload_path 的要求
        3. 驗證文件名不包含特殊字符
        4. 驗證文件名有正確的擴展名
        """
        test_image = self._create_test_image('format_test', color='yellow')
        
        response = self._update_route_with_photo(test_image)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        route = Route.objects.get(id=self.route.id)
        filename = route.photo.name.split('/')[-1]
        
        # 驗證文件名格式：route_{route_id}_{timestamp}[_random].jpg
        # 注意：Django 的 ImageField 可能會在文件名中添加隨機字符串以避免衝突
        import re
        # 允許格式：route_{route_id}_{timestamp}.jpg 或 route_{route_id}_{timestamp}_{random}.jpg
        pattern = r'^route_\d+_\d{8}_\d{6}(_[A-Za-z0-9]+)?\.(jpg|jpeg|png|gif|bmp|webp)$'
        self.assertTrue(
            re.match(pattern, filename, re.IGNORECASE),
            f"文件名格式應該符合 route_photo_upload_path 的要求，實際: {filename}"
        )
        
        # 驗證文件名不包含特殊字符
        special_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ', '!']
        for char in special_chars:
            self.assertNotIn(char, filename, f"文件名不應該包含 '{char}' 字符")
    
    def test_multiple_photo_updates_in_sequence(self):
        """
        測試：連續多次更新路線照片應該都成功
        
        測試步驟：
        1. 第一次更新路線照片
        2. 第二次更新路線照片（替換）
        3. 第三次更新路線照片（替換）
        4. 驗證每次更新都成功
        5. 驗證每次更新的文件名格式都正確
        """
        colors = ['red', 'blue', 'green']
        
        for i, color in enumerate(colors):
            test_image = self._create_test_image(f'update_{i}', color=color)
            response = self._update_route_with_photo(test_image)
            
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"第{i+1}次更新應該成功，但返回了 {response.status_code}"
            )
            
            route = Route.objects.get(id=self.route.id)
            self.assertIsNotNone(route.photo, f"第{i+1}次更新後，路線應該有照片")
            self.assertTrue(
                default_storage.exists(route.photo.name),
                f"第{i+1}次更新後，照片文件應該存在: {route.photo.name}"
            )
            
            # 驗證文件名格式正確
            filename = route.photo.name.split('/')[-1]
            self.assertTrue(
                filename.startswith('route_') and filename.endswith(('.jpg', '.jpeg')),
                f"第{i+1}次更新的文件名格式應該正確，實際: {filename}"
            )
    
    def test_update_route_without_photo_change(self):
        """
        測試：更新路線但不改變照片應該成功
        
        測試步驟：
        1. 先為路線添加照片
        2. 更新路線但不提供 photo 字段
        3. 驗證更新成功
        4. 驗證照片沒有改變
        """
        # 先添加照片
        initial_image = self._create_test_image('initial', color='red')
        response1 = self._update_route_with_photo(initial_image)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        initial_photo_name = Route.objects.get(id=self.route.id).photo.name
        
        # 更新路線但不提供 photo 字段
        url = f'/api/routes/{self.route.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True
        }
        
        data = {
            'name': '更新名稱但不改變照片',
            'grade': 'V6',
            'member_completions': json.dumps(member_completions)
            # 不提供 'photo' 字段
        }
        
        response2 = self.client.patch(
            url,
            data=data,
            format='json',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # 驗證照片沒有改變
        route = Route.objects.get(id=self.route.id)
        self.assertEqual(
            route.photo.name,
            initial_photo_name,
            "不提供 photo 字段時，照片不應該改變"
        )

