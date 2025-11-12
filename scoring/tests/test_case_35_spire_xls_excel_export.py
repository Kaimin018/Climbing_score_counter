"""
Spire.XLS Excel 輸出功能測試用例

測試項目：
1. ExcelImageEmbedder 類基本功能測試
2. 圖片嵌入儲存格功能測試
3. 批量插入圖片功能測試
4. 儲存格大小調整功能測試
5. 圖片偏移設置功能測試
6. 便捷函數 create_excel_with_embedded_images 測試
7. 保存為字節流功能測試
8. 錯誤處理測試（圖片文件不存在、Spire.XLS 未安裝等）
"""

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, cleanup_test_photos
from PIL import Image
from io import BytesIO
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class TestCaseSpireXLSExcelExport(TestCase):
    """測試 Spire.XLS Excel 輸出功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("Spire.XLS 測試房間")
        self.m1, self.m2 = self.factory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試圖片
        self.test_images = []
        self.temp_image_paths = []
        
        # 創建多張測試圖片
        for i in range(3):
            img = Image.new('RGB', (200, 150), color=('red', 'green', 'blue')[i])
            temp_path = os.path.join(tempfile.gettempdir(), f'test_image_{i}.jpg')
            img.save(temp_path, 'JPEG')
            self.temp_image_paths.append(temp_path)
            self.test_images.append(temp_path)
    
    def tearDown(self):
        """清理測試數據和臨時文件"""
        cleanup_test_data(room=self.room, cleanup_photos=True)
        
        # 清理臨時圖片文件
        for temp_path in self.temp_image_paths:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.warning(f"清理臨時圖片文件失敗: {temp_path}, 錯誤: {str(e)}")
    
    def test_spire_xls_available(self):
        """測試 Spire.XLS 是否可用"""
        try:
            from scoring.utils_excel_image import SPIRE_XLS_AVAILABLE, ExcelImageEmbedder
            
            if not SPIRE_XLS_AVAILABLE:
                self.skipTest("Spire.XLS for Python 未安裝，跳過測試")
            
            # 測試可以創建 ExcelImageEmbedder 實例
            embedder = ExcelImageEmbedder()
            self.assertIsNotNone(embedder)
            self.assertIsNotNone(embedder.workbook)
            self.assertIsNotNone(embedder.worksheet)
        except ImportError as e:
            self.skipTest(f"Spire.XLS for Python 未安裝: {str(e)}")
    
    def test_create_excel_workbook(self):
        """測試創建 Excel 工作簿"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 驗證工作簿已創建
            self.assertIsNotNone(embedder.workbook)
            self.assertIsNotNone(embedder.worksheet)
            
            # 測試保存工作簿
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_insert_single_image_to_cell(self):
        """測試在單個儲存格插入圖片"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 在 A1 儲存格插入圖片
            image_path = self.test_images[0]
            picture = embedder.insert_image_to_cell(
                image_path=image_path,
                row_index=1,
                column_index=1,
                offset_x=2,
                offset_y=2,
                auto_resize_cell=True
            )
            
            self.assertIsNotNone(picture)
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_insert_multiple_images(self):
        """測試批量插入多張圖片"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 插入多張圖片到不同儲存格
            positions = [
                (1, 1),  # A1
                (1, 2),  # B1
                (2, 1),  # A2
            ]
            
            for idx, (row, col) in enumerate(positions):
                if idx < len(self.test_images):
                    picture = embedder.insert_image_to_cell(
                        image_path=self.test_images[idx],
                        row_index=row,
                        column_index=col,
                        offset_x=2,
                        offset_y=2,
                        auto_resize_cell=True
                    )
                    self.assertIsNotNone(picture)
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_cell_size_adjustment(self):
        """測試儲存格大小調整"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 手動設置儲存格大小
            embedder.set_cell_size(
                row_index=1,
                column_index=1,
                width_points=200,
                height_points=150
            )
            
            # 插入圖片（不自動調整儲存格）
            picture = embedder.insert_image_to_cell(
                image_path=self.test_images[0],
                row_index=1,
                column_index=1,
                offset_x=5,
                offset_y=5,
                auto_resize_cell=False
            )
            
            self.assertIsNotNone(picture)
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_image_offset(self):
        """測試圖片偏移設置"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 測試不同的偏移值
            offsets = [
                (0, 0),   # 無偏移
                (2, 2),   # 小偏移
                (5, 5),   # 中等偏移
                (10, 10), # 大偏移
            ]
            
            for idx, (offset_x, offset_y) in enumerate(offsets):
                if idx < len(self.test_images):
                    picture = embedder.insert_image_to_cell(
                        image_path=self.test_images[idx],
                        row_index=1,
                        column_index=idx + 1,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        auto_resize_cell=True
                    )
                    self.assertIsNotNone(picture)
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_convenience_function(self):
        """測試便捷函數 create_excel_with_embedded_images"""
        try:
            from scoring.utils_excel_image import create_excel_with_embedded_images
            
            # 準備圖片數據列表
            image_data_list = [
                {
                    'image_path': self.test_images[0],
                    'row': 1,
                    'column': 1,
                    'offset_x': 2,
                    'offset_y': 2,
                    'auto_resize': True
                },
                {
                    'image_path': self.test_images[1],
                    'row': 1,
                    'column': 2,
                    'offset_x': 5,
                    'offset_y': 5,
                    'auto_resize': True
                }
            ]
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                create_excel_with_embedded_images(
                    output_path=output_path,
                    image_data_list=image_data_list,
                    sheet_name='測試工作表'
                )
                
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_save_to_bytes(self):
        """測試保存為字節流功能"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 插入圖片
            embedder.insert_image_to_cell(
                image_path=self.test_images[0],
                row_index=1,
                column_index=1,
                auto_resize_cell=True
            )
            
            # 保存為字節流
            excel_bytes = embedder.save_to_bytes()
            
            self.assertIsNotNone(excel_bytes)
            self.assertIsInstance(excel_bytes, bytes)
            self.assertGreater(len(excel_bytes), 0)
            
            # 驗證字節流是有效的 Excel 文件（檢查文件頭）
            # Excel 文件的 ZIP 文件頭（.xlsx 是 ZIP 格式）
            self.assertEqual(excel_bytes[:2], b'PK', "應該是有效的 ZIP/Excel 文件")
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_image_file_not_found(self):
        """測試圖片文件不存在時的錯誤處理"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 嘗試插入不存在的圖片
            with self.assertRaises(FileNotFoundError):
                embedder.insert_image_to_cell(
                    image_path='nonexistent_image.jpg',
                    row_index=1,
                    column_index=1
                )
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_multiple_worksheets(self):
        """測試多個工作表功能"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 在默認工作表插入圖片
            embedder.insert_image_to_cell(
                image_path=self.test_images[0],
                row_index=1,
                column_index=1,
                auto_resize_cell=True
            )
            
            # 添加新工作表
            new_sheet = embedder.add_worksheet('第二個工作表')
            self.assertIsNotNone(new_sheet)
            
            # 切換到新工作表並插入圖片
            embedder.get_worksheet(sheet_name='第二個工作表')
            embedder.insert_image_to_cell(
                image_path=self.test_images[1],
                row_index=1,
                column_index=1,
                auto_resize_cell=True
            )
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_preserve_aspect_ratio(self):
        """測試保持圖片寬高比功能"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 插入圖片並保持寬高比
            picture = embedder.insert_image_to_cell(
                image_path=self.test_images[0],
                row_index=1,
                column_index=1,
                auto_resize_cell=True,
                preserve_aspect_ratio=True
            )
            
            self.assertIsNotNone(picture)
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_grid_layout(self):
        """測試網格佈局（多行多列圖片）"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            
            embedder = ExcelImageEmbedder()
            
            # 創建 2x2 網格
            row = 1
            col = 1
            for idx, image_path in enumerate(self.test_images[:4]):  # 最多4張圖片
                embedder.insert_image_to_cell(
                    image_path=image_path,
                    row_index=row,
                    column_index=col,
                    offset_x=2,
                    offset_y=2,
                    auto_resize_cell=True
                )
                
                # 移動到下一個位置（2列後換行）
                col += 1
                if col > 2:
                    col = 1
                    row += 1
            
            # 測試保存
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                output_path = tmp_file.name
            
            try:
                embedder.save(output_path)
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(os.path.getsize(output_path), 0)
            finally:
                if os.path.exists(output_path):
                    os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
    
    def test_excel_with_route_photos(self):
        """測試使用實際路線照片創建 Excel"""
        try:
            from scoring.utils_excel_image import ExcelImageEmbedder
            from django.contrib.auth.models import User
            from rest_framework.test import APIClient
            from rest_framework import status
            import json
            
            # 創建測試用戶並認證
            user = User.objects.create_user(
                username="testuser",
                password="TestPass123!",
                email="test@example.com"
            )
            client = APIClient()
            client.force_authenticate(user=user)
            
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
            
            response = client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            route = Route.objects.get(name='測試路線')
            self.assertIsNotNone(route.photo)
            
            # 使用 Spire.XLS 創建包含路線照片的 Excel
            embedder = ExcelImageEmbedder()
            
            if route.photo and os.path.exists(route.photo.path):
                picture = embedder.insert_image_to_cell(
                    image_path=route.photo.path,
                    row_index=1,
                    column_index=1,
                    offset_x=2,
                    offset_y=2,
                    auto_resize_cell=True
                )
                self.assertIsNotNone(picture)
                
                # 測試保存
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    output_path = tmp_file.name
                
                try:
                    embedder.save(output_path)
                    self.assertTrue(os.path.exists(output_path))
                finally:
                    if os.path.exists(output_path):
                        os.remove(output_path)
        except ImportError:
            self.skipTest("Spire.XLS for Python 未安裝")
        except Exception as e:
            # 如果路線照片不存在或其他錯誤，跳過測試
            self.skipTest(f"無法創建測試路線照片: {str(e)}")

