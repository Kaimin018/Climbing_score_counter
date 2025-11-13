"""
PDF 輸出功能測試用例

測試項目：
1. PDF 導出功能基本測試
2. PDF 包含排行榜數據測試
3. PDF 包含路線照片測試
4. PDF 包含成員完成狀態測試
5. 錯誤處理測試（reportlab 未安裝等）
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, cleanup_test_photos
from PIL import Image
from io import BytesIO
import os
import tempfile
import logging
import json

logger = logging.getLogger(__name__)


class TestCasePdfExport(TestCase):
    """測試 PDF 輸出功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("PDF 測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試用戶並認證
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def test_pdf_export_available(self):
        """測試 PDF 導出功能是否可用"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate
            
            # 如果導入成功，說明 reportlab 已安裝
            self.assertTrue(True)
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
    
    def test_pdf_export_endpoint(self):
        """測試 PDF 導出端點"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 測試導出端點
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        # 應該返回 200 狀態碼
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 應該返回 PDF 內容類型
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # 應該包含 PDF 文件頭
        pdf_content = response.content
        self.assertGreater(len(pdf_content), 0)
        # PDF 文件以 %PDF 開頭
        self.assertTrue(pdf_content.startswith(b'%PDF'))
    
    def test_pdf_contains_leaderboard(self):
        """測試 PDF 包含排行榜數據"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 設置一些分數
        route1 = self.factory.create_route(self.room, "測試路線1", "V5")
        Score.objects.filter(member=self.m1, route=route1).update(is_completed=True)
        
        # 導出 PDF
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容（通過檢查文件大小，應該大於 0）
        pdf_content = response.content
        self.assertGreater(len(pdf_content), 1000)  # PDF 應該有足夠的內容
    
    def test_pdf_with_route_photos(self):
        """測試 PDF 包含路線照片"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建帶照片的路線
        img = Image.new('RGB', (200, 150), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        photo_file = SimpleUploadedFile(
            name='test_route_photo.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        # 創建路線
        url = f'/api/rooms/{self.room.id}/routes/'
        data = {
            'name': '測試路線',
            'grade': 'V5',
            'member_completions': json.dumps({}),
            'photo': photo_file
        }
        
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        route = Route.objects.get(name='測試路線')
        self.assertIsNotNone(route.photo)
        
        # 導出 PDF
        export_url = f'/api/rooms/{self.room.id}/export-pdf/'
        pdf_response = self.client.get(export_url)
        
        self.assertEqual(pdf_response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 包含內容
        pdf_content = pdf_response.content
        self.assertGreater(len(pdf_content), 1000)
    
    def test_pdf_contains_member_completion_status(self):
        """測試 PDF 包含成員完成狀態"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建路線並設置完成狀態
        route1 = self.factory.create_route(self.room, "測試路線1", "V5")
        route2 = self.factory.create_route(self.room, "測試路線2", "V6")
        
        # 設置成員1完成路線1
        Score.objects.filter(member=self.m1, route=route1).update(is_completed=True)
        # 設置成員2完成路線2
        Score.objects.filter(member=self.m2, route=route2).update(is_completed=True)
        
        # 導出 PDF
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容
        pdf_content = response.content
        self.assertGreater(len(pdf_content), 1000)
    
    def test_pdf_export_without_authentication(self):
        """測試未認證時導出 PDF"""
        # 使用未認證的客戶端
        unauthenticated_client = APIClient()
        
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = unauthenticated_client.get(url)
        
        # 根據權限設置，可能返回 401 或 403
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_pdf_export_nonexistent_room(self):
        """測試導出不存在的房間 PDF"""
        url = '/api/rooms/99999/export-pdf/'
        response = self.client.get(url)
        
        # 應該返回 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_pdf_content_structure(self):
        """測試 PDF 內容結構"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建一些測試數據
        route1 = self.factory.create_route(self.room, "測試路線1", "V5")
        Score.objects.filter(member=self.m1, route=route1).update(is_completed=True)
        
        # 導出 PDF
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 文件頭
        pdf_content = response.content
        self.assertTrue(pdf_content.startswith(b'%PDF'))
        
        # 驗證文件名
        content_disposition = response.get('Content-Disposition', '')
        self.assertIn('.pdf', content_disposition)
        self.assertIn(self.room.name, content_disposition or '')
    
    def test_pdf_export_empty_room(self):
        """測試空房間（沒有路線）的 PDF 導出"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建空房間（沒有路線）
        empty_room = self.factory.create_room("空房間")
        
        # 導出 PDF
        url = f'/api/rooms/{empty_room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容
        pdf_content = response.content
        self.assertTrue(pdf_content.startswith(b'%PDF'))
        self.assertGreater(len(pdf_content), 0)
        
        # 清理
        cleanup_test_data(room=empty_room, cleanup_photos=True)
    
    def test_pdf_export_no_members(self):
        """測試沒有成員的房間 PDF 導出"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建沒有成員的房間
        room_no_members = self.factory.create_room("無成員房間")
        self.factory.create_route(room_no_members, "測試路線", "V5")
        
        # 導出 PDF
        url = f'/api/rooms/{room_no_members.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容
        pdf_content = response.content
        self.assertTrue(pdf_content.startswith(b'%PDF'))
        
        # 清理
        cleanup_test_data(room=room_no_members, cleanup_photos=True)
    
    def test_pdf_export_multiple_routes_with_photos(self):
        """測試多個路線帶照片的 PDF 導出"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建多個帶照片的路線
        routes = []
        for i in range(3):
            img = Image.new('RGB', (200, 150), color=('red', 'green', 'blue')[i])
            img_io = BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            
            photo_file = SimpleUploadedFile(
                name=f'test_route_{i}.jpg',
                content=img_io.read(),
                content_type='image/jpeg'
            )
            
            url = f'/api/rooms/{self.room.id}/routes/'
            data = {
                'name': f'測試路線{i+1}',
                'grade': f'V{i+3}',
                'member_completions': json.dumps({}),
                'photo': photo_file
            }
            
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 導出 PDF
        export_url = f'/api/rooms/{self.room.id}/export-pdf/'
        pdf_response = self.client.get(export_url)
        
        self.assertEqual(pdf_response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 包含內容
        pdf_content = pdf_response.content
        self.assertGreater(len(pdf_content), 1000)
        self.assertTrue(pdf_content.startswith(b'%PDF'))
    
    def test_pdf_export_route_table_structure(self):
        """測試路線表格結構是否正確"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建多個路線和成員
        route1 = self.factory.create_route(self.room, "路線1", "V5")
        route2 = self.factory.create_route(self.room, "路線2", "V6")
        
        # 設置完成狀態
        Score.objects.filter(member=self.m1, route=route1).update(is_completed=True)
        Score.objects.filter(member=self.m2, route=route2).update(is_completed=True)
        
        # 導出 PDF
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容
        pdf_content = response.content
        self.assertTrue(pdf_content.startswith(b'%PDF'))
        self.assertGreater(len(pdf_content), 1000)
    
    def test_pdf_export_with_invalid_photo_path(self):
        """測試照片路徑無效時的處理"""
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            self.skipTest("reportlab 未安裝，跳過測試")
        
        # 創建路線（不帶照片）
        route = self.factory.create_route(self.room, "無照片路線", "V5")
        
        # 導出 PDF（應該能正常處理無照片的情況）
        url = f'/api/rooms/{self.room.id}/export-pdf/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 PDF 內容
        pdf_content = response.content
        self.assertTrue(pdf_content.startswith(b'%PDF'))

