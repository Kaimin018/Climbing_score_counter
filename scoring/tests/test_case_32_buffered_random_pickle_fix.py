"""
測試案例：修復 BufferedRandom 對象 pickle 錯誤

測試場景：
1. 創建路線時使用 BufferedRandom 類型的文件對象
2. 更新路線時使用 BufferedRandom 類型的文件對象
3. 驗證文件對象被正確轉換為 InMemoryUploadedFile
4. 驗證不會出現 pickle 錯誤
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.storage import default_storage
from PIL import Image
from io import BytesIO, BufferedRandom, BufferedReader
import tempfile
import os
import json
import logging

from scoring.models import Room, Member, Route
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data

logger = logging.getLogger(__name__)


class TestCaseBufferedRandomPickleFix(TestCase):
    """測試 BufferedRandom 對象 pickle 錯誤修復"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("測試房間")
        self.m1 = self.factory.create_normal_members(self.room, count=1)[0]
        self.m2 = self.factory.create_normal_members(self.room, count=1)[0]
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def _create_buffered_random_file(self, name='test_photo.jpg', format='JPEG', color='red', size=(800, 600)):
        """
        創建一個 BufferedRandom 類型的文件對象（模擬真實文件系統中的文件）
        這會觸發 pickle 錯誤，如果沒有修復的話
        """
        # 創建臨時文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file_path = temp_file.name
        temp_file.close()
        
        try:
            # 創建圖片並保存到臨時文件
            img = Image.new('RGB', size, color=color)
            img.save(temp_file_path, format=format)
            
            # 打開文件為 BufferedRandom 或 BufferedReader 對象（這會觸發 pickle 錯誤）
            # 在 Windows 上，'rb' 模式返回 BufferedReader，'r+b' 模式返回 BufferedRandom
            # 我們的修復代碼會處理這兩種情況
            file_obj = open(temp_file_path, 'r+b')  # 使用 'r+b' 模式以獲得 BufferedRandom
            
            # 創建模擬的上傳文件對象，包含 BufferedRandom
            from django.core.files.uploadedfile import UploadedFile
            
            # 創建一個包裝類，模擬真實的上傳文件
            class BufferedRandomUploadedFile(UploadedFile):
                def __init__(self, file_obj, name, content_type):
                    self.file = file_obj
                    self.name = name
                    self.content_type = content_type
                    self.size = os.path.getsize(file_obj.name)
                
                def read(self, size=-1):
                    return self.file.read(size)
                
                def seek(self, pos):
                    return self.file.seek(pos)
                
                def close(self):
                    self.file.close()
                    # 清理臨時文件
                    if os.path.exists(self.file.name):
                        os.unlink(self.file.name)
            
            uploaded_file = BufferedRandomUploadedFile(
                file_obj,
                name,
                f'image/{format.lower()}'
            )
            
            return uploaded_file, temp_file_path
            
        except Exception as e:
            # 清理臨時文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise
    
    def test_create_route_with_buffered_random_file(self):
        """測試：使用 BufferedRandom 文件對象創建路線"""
        logger.info("測試：使用 BufferedRandom 文件對象創建路線")
        
        # 創建 BufferedRandom 文件對象
        photo_file, temp_path = self._create_buffered_random_file('test_photo.jpg')
        
        try:
            # 驗證文件對象類型（BufferedRandom 或 BufferedReader，兩者都會觸發 pickle 錯誤）
            self.assertTrue(
                isinstance(photo_file.file, BufferedRandom) or isinstance(photo_file.file, BufferedReader),
                f"文件對象應該是 BufferedRandom 或 BufferedReader 類型，實際類型: {type(photo_file.file)}"
            )
            
            member_completions = {
                str(self.m1.id): True,
                str(self.m2.id): False
            }
            
            data = {
                'name': '【路線】測試路線',
                'grade': 'V4',
                'member_completions': json.dumps(member_completions),
                'photo': photo_file
            }
            
            # 創建路線（使用 RoomViewSet 的 create_route action，這樣會自動設置 room context）
            url = f'/api/rooms/{self.room.id}/routes/'
            response = self.client.post(
                url,
                data=data,
                format='multipart'
            )
            
            # 驗證響應
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"創建路線應該成功，但返回了 {response.status_code}。"
                f"錯誤: {response.data if hasattr(response, 'data') else response.content}"
            )
            
            # 驗證路線已創建
            route_id = response.data['id']
            route = Route.objects.get(id=route_id)
            self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
            
            # 驗證照片文件存在
            self.assertTrue(
                default_storage.exists(route.photo.name),
                f"照片文件應該存在: {route.photo.name}"
            )
            
            # 驗證 API 響應包含照片 URL
            self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
            self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
            
            logger.info("✅ 測試通過：使用 BufferedRandom 文件對象創建路線成功")
            
        finally:
            # 清理
            try:
                photo_file.close()
            except:
                pass
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def test_update_route_with_buffered_random_file(self):
        """測試：使用 BufferedRandom 文件對象更新路線"""
        logger.info("測試：使用 BufferedRandom 文件對象更新路線")
        
        # 先創建一個路線
        route = self.factory.create_route(
            room=self.room,
            name="原始路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        # 創建 BufferedRandom 文件對象
        photo_file, temp_path = self._create_buffered_random_file('update_photo.jpg')
        
        try:
            # 驗證文件對象類型（BufferedRandom 或 BufferedReader，兩者都會觸發 pickle 錯誤）
            self.assertTrue(
                isinstance(photo_file.file, BufferedRandom) or isinstance(photo_file.file, BufferedReader),
                f"文件對象應該是 BufferedRandom 或 BufferedReader 類型，實際類型: {type(photo_file.file)}"
            )
            
            member_completions = {
                str(self.m1.id): True,
                str(self.m2.id): True
            }
            
            data = {
                'name': '【路線】更新後的路線',
                'grade': 'V5',
                'member_completions': json.dumps(member_completions),
                'photo': photo_file
            }
            
            # 更新路線
            url = f'/api/routes/{route.id}/'
            response = self.client.patch(
                url,
                data=data,
                format='multipart'
            )
            
            # 驗證響應
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"更新路線應該成功，但返回了 {response.status_code}。"
                f"錯誤: {response.data if hasattr(response, 'data') else response.content}"
            )
            
            # 驗證路線已更新
            route.refresh_from_db()
            self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
            
            # 驗證照片文件存在
            self.assertTrue(
                default_storage.exists(route.photo.name),
                f"照片文件應該存在: {route.photo.name}"
            )
            
            # 驗證 API 響應包含照片 URL
            self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
            self.assertNotEqual(response.data['photo_url'], '', "photo_url 不應該為空")
            
            logger.info("✅ 測試通過：使用 BufferedRandom 文件對象更新路線成功")
            
        finally:
            # 清理
            try:
                photo_file.close()
            except:
                pass
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def test_create_route_with_buffered_reader_file(self):
        """測試：使用 BufferedReader 文件對象創建路線"""
        logger.info("測試：使用 BufferedReader 文件對象創建路線")
        
        # 創建臨時文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file_path = temp_file.name
        temp_file.close()
        
        try:
            # 創建圖片並保存到臨時文件
            img = Image.new('RGB', (800, 600), color='blue')
            img.save(temp_file_path, format='JPEG')
            
            # 打開文件為 BufferedReader 對象
            from io import BufferedReader
            file_obj = open(temp_file_path, 'rb')
            
            # 創建模擬的上傳文件對象
            from django.core.files.uploadedfile import UploadedFile
            
            class BufferedReaderUploadedFile(UploadedFile):
                def __init__(self, file_obj, name, content_type):
                    self.file = file_obj
                    self.name = name
                    self.content_type = content_type
                    self.size = os.path.getsize(file_obj.name)
                
                def read(self, size=-1):
                    return self.file.read(size)
                
                def seek(self, pos):
                    return self.file.seek(pos)
                
                def close(self):
                    self.file.close()
                    if os.path.exists(self.file.name):
                        os.unlink(self.file.name)
            
            photo_file = BufferedReaderUploadedFile(
                file_obj,
                'test_photo.jpg',
                'image/jpeg'
            )
            
            # 驗證文件對象類型（BufferedReader，在 Windows 上 'rb' 模式返回此類型）
            self.assertIsInstance(photo_file.file, BufferedReader,
                                f"文件對象應該是 BufferedReader 類型，實際類型: {type(photo_file.file)}")
            
            member_completions = {
                str(self.m1.id): True,
                str(self.m2.id): False
            }
            
            data = {
                'name': '【路線】測試路線',
                'grade': 'V4',
                'member_completions': json.dumps(member_completions),
                'photo': photo_file
            }
            
            # 創建路線（使用 RoomViewSet 的 create_route action，這樣會自動設置 room context）
            url = f'/api/rooms/{self.room.id}/routes/'
            response = self.client.post(
                url,
                data=data,
                format='multipart'
            )
            
            # 驗證響應
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"創建路線應該成功，但返回了 {response.status_code}。"
                f"錯誤: {response.data if hasattr(response, 'data') else response.content}"
            )
            
            # 驗證路線已創建
            route_id = response.data['id']
            route = Route.objects.get(id=route_id)
            self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
            
            logger.info("✅ 測試通過：使用 BufferedReader 文件對象創建路線成功")
            
        finally:
            # 清理
            try:
                photo_file.close()
            except:
                pass
            if os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def test_update_route_replace_photo_with_buffered_random(self):
        """測試：使用 BufferedRandom 文件對象替換現有照片"""
        logger.info("測試：使用 BufferedRandom 文件對象替換現有照片")
        
        # 先創建一個有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="有照片的路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        # 添加初始照片
        from django.core.files.uploadedfile import SimpleUploadedFile
        initial_img = Image.new('RGB', (100, 100), color='green')
        initial_img_io = BytesIO()
        initial_img.save(initial_img_io, format='JPEG')
        initial_img_io.seek(0)
        initial_photo = SimpleUploadedFile(
            'initial.jpg',
            initial_img_io.read(),
            content_type='image/jpeg'
        )
        route.photo = initial_photo
        route.save()
        
        old_photo_name = route.photo.name
        
        # 創建新的 BufferedRandom 文件對象
        photo_file, temp_path = self._create_buffered_random_file('new_photo.jpg', color='purple')
        
        try:
            member_completions = {
                str(self.m1.id): True,
                str(self.m2.id): True
            }
            
            data = {
                'name': '【路線】有照片的路線',
                'grade': 'V4',
                'member_completions': json.dumps(member_completions),
                'photo': photo_file
            }
            
            # 更新路線
            url = f'/api/routes/{route.id}/'
            response = self.client.patch(
                url,
                data=data,
                format='multipart'
            )
            
            # 驗證響應
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"更新路線應該成功，但返回了 {response.status_code}。"
                f"錯誤: {response.data if hasattr(response, 'data') else response.content}"
            )
            
            # 驗證路線已更新
            route.refresh_from_db()
            self.assertIsNotNone(route.photo, "路線應該有新的圖片")
            self.assertNotEqual(route.photo.name, old_photo_name,
                              "圖片文件名應該不同（新圖片）")
            
            # 驗證新照片文件存在
            self.assertTrue(
                default_storage.exists(route.photo.name),
                f"新照片文件應該存在: {route.photo.name}"
            )
            
            logger.info("✅ 測試通過：使用 BufferedRandom 文件對象替換照片成功")
            
        finally:
            # 清理
            try:
                photo_file.close()
            except:
                pass
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

