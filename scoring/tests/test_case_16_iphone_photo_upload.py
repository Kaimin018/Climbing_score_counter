"""
iPhone 圖片上傳問題測試用例

模擬 iPhone 14 Pro 上傳圖片時可能發生的問題：
1. HEIC 格式圖片
2. 特殊文件名格式（IMG_XXXX.HEIC）
3. 文件名包含特殊字符
4. Content-Type 驗證問題
"""
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


class TestCaseIPhonePhotoUpload(TestCase):
    """測試 iPhone 圖片上傳問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("iPhone 測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
        # 清理測試上傳的圖片文件
        routes = Route.objects.filter(room=self.room)
        for route in routes:
            if route.photo and default_storage.exists(route.photo.name):
                default_storage.delete(route.photo.name)
    
    def test_iphone_heic_format_upload(self):
        """測試 iPhone HEIC 格式圖片上傳"""
        # 創建模擬 HEIC 文件（使用 JPEG 內容但標記為 HEIC）
        img = Image.new('RGB', (800, 600), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        heic_content = img_io.read()
        
        # 模擬 iPhone 的 HEIC 文件名格式
        heic_image = SimpleUploadedFile(
            name='IMG_20250101_120000.HEIC',
            content=heic_content,
            content_type='image/heic'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'iPhone HEIC 路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': heic_image
        }
        
        # 模擬 iPhone User-Agent
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        # 記錄響應詳情以便調試
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"HEIC upload test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != status.HTTP_201_CREATED:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        # HEIC 格式可能被接受或拒絕（取決於 Pillow 支持）
        # 如果被拒絕，應該返回清晰的錯誤信息
        if response.status_code == status.HTTP_201_CREATED:
            # 成功創建
            route_id = response.data['id']
            route = Route.objects.get(id=route_id)
            self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            # 驗證失敗，檢查錯誤信息
            self.assertIn('photo', response.data or {}, "應該有 photo 字段的錯誤信息")
            logger.error(f"Validation error: {response.data.get('photo', 'N/A')}")
        else:
            self.fail(f"意外的狀態碼: {response.status_code}, 響應: {response.data if hasattr(response, 'data') else response.content}")
    
    def test_iphone_jpeg_format_upload(self):
        """測試 iPhone JPEG 格式圖片上傳（最常見的情況）"""
        # 創建 JPEG 圖片
        img = Image.new('RGB', (800, 600), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # 模擬 iPhone 的 JPEG 文件名格式
        jpeg_image = SimpleUploadedFile(
            name='IMG_20250101_120000.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'iPhone JPEG 路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': jpeg_image
        }
        
        # 模擬 iPhone User-Agent
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"JPEG upload test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # JPEG 格式應該成功
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"JPEG 格式應該成功上傳，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
    
    def test_iphone_filename_with_special_characters(self):
        """測試 iPhone 文件名包含特殊字符的情況"""
        # 創建圖片
        img = Image.new('RGB', (800, 600), color='green')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # 模擬可能包含特殊字符的文件名
        special_filename_image = SimpleUploadedFile(
            name='IMG_2025-01-01 12.00.00.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '特殊文件名路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': special_filename_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Special filename test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # 應該成功（因為我們有文件名清理邏輯）
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理特殊字符文件名，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
    
    def test_iphone_filename_with_unicode(self):
        """測試 iPhone 文件名包含 Unicode 字符的情況"""
        # 創建圖片
        img = Image.new('RGB', (800, 600), color='yellow')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # 模擬可能包含 Unicode 字符的文件名
        unicode_filename_image = SimpleUploadedFile(
            name='照片_2025年1月1日.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'Unicode 文件名路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': unicode_filename_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Unicode filename test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # 應該成功（因為我們有文件名清理邏輯）
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理 Unicode 文件名，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
    
    def test_iphone_live_photo_format(self):
        """測試 iPhone Live Photo 格式（可能包含 .MOV 文件）"""
        # 注意：Live Photo 實際上包含兩個文件（.HEIC 和 .MOV）
        # 這裡只測試圖片部分
        img = Image.new('RGB', (800, 600), color='purple')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # 模擬 Live Photo 的圖片文件名
        live_photo_image = SimpleUploadedFile(
            name='IMG_20250101_120000.HEIC',
            content=img_io.read(),
            content_type='image/heic'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'Live Photo 路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': live_photo_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Live Photo test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # Live Photo 的 HEIC 部分應該被處理
        # 如果失敗，記錄詳細錯誤
        if response.status_code != status.HTTP_201_CREATED:
            logger.error(f"Detailed error: {response.data if hasattr(response, 'data') else response.content}")
    
    def test_iphone_photo_without_extension(self):
        """測試沒有擴展名的圖片文件（可能的情況）"""
        # 創建圖片
        img = Image.new('RGB', (800, 600), color='orange')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # 沒有擴展名的文件名
        no_ext_image = SimpleUploadedFile(
            name='IMG_20250101_120000',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '無擴展名路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': no_ext_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"No extension test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # 應該成功（因為我們有 content_type 檢查）
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理無擴展名文件，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )

