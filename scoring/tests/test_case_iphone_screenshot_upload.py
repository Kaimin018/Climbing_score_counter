"""
iPhone 屏幕截圖上傳問題測試用例

模擬 iPhone 屏幕截圖上傳時可能發生的問題：
1. PNG 格式圖片
2. 中文文件名（如"屏幕快照"）
3. 文件名包含特殊字符或空格
4. 文件名可能沒有擴展名
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


class TestCaseIPhoneScreenshotUpload(TestCase):
    """測試 iPhone 屏幕截圖上傳問題"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("iPhone 截圖測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def test_iphone_screenshot_chinese_filename(self):
        """測試 iPhone 屏幕截圖（中文文件名：屏幕快照）"""
        # 創建 PNG 圖片（iPhone 截圖通常是 PNG 格式）
        img = Image.new('RGB', (800, 600), color='red')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # 模擬 iPhone 屏幕截圖的文件名格式（中文）
        screenshot_image = SimpleUploadedFile(
            name='屏幕快照 2025-01-01 12.00.00.png',
            content=img_io.read(),
            content_type='image/png'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'iPhone 截圖路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': screenshot_image
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
        logger.info(f"iPhone screenshot (Chinese filename) test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != status.HTTP_201_CREATED:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        # 應該成功
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理中文文件名截圖，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線創建成功
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(route.photo.name.startswith('route_photos/'), 
                       f"圖片應該保存在 route_photos/ 目錄下，實際: {route.photo.name}")
        
        # 驗證圖片文件存在
        self.assertTrue(default_storage.exists(route.photo.name),
                       f"圖片文件應該存在: {route.photo.name}")
    
    def test_iphone_screenshot_english_filename(self):
        """測試 iPhone 屏幕截圖（英文文件名：Screenshot）"""
        # 創建 PNG 圖片
        img = Image.new('RGB', (800, 600), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # 模擬 iPhone 屏幕截圖的文件名格式（英文）
        screenshot_image = SimpleUploadedFile(
            name='Screenshot 2025-01-01 at 12.00.00 PM.png',
            content=img_io.read(),
            content_type='image/png'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': 'iPhone Screenshot 路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': screenshot_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"iPhone screenshot (English filename) test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # 應該成功
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理英文文件名截圖，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線創建成功
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
    
    def test_iphone_screenshot_no_extension(self):
        """測試 iPhone 屏幕截圖（沒有擴展名）"""
        # 創建 PNG 圖片
        img = Image.new('RGB', (800, 600), color='green')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        # 沒有擴展名的文件名
        screenshot_image = SimpleUploadedFile(
            name='屏幕快照 2025-01-01 12.00.00',
            content=img_io.read(),
            content_type='image/png'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '無擴展名截圖路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': screenshot_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        )
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"iPhone screenshot (no extension) test - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        
        # 應該成功（因為我們有 content_type 檢查）
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"應該成功處理無擴展名截圖，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線創建成功
        route_id = response.data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        # 驗證文件名應該有 .png 擴展名
        self.assertTrue(route.photo.name.endswith('.png'), 
                       f"圖片文件名應該以 .png 結尾，實際: {route.photo.name}")

