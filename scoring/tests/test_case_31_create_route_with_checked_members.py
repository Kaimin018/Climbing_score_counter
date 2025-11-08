"""
創建路線時直接勾選已通過成員的測試用例

測試項目：
1. 新增路線，填入路線名稱、等級、照片，並選取有通過的人員，點選創建路線應該成功
2. 驗證創建後成員的完成狀態正確
3. 驗證照片上傳成功
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


class TestCaseCreateRouteWithCheckedMembers(TestCase):
    """測試創建路線時直接勾選已通過成員"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("勾選成員測試房間")
        self.m1, self.m2, self.m3 = self.factory.create_normal_members(
            self.room,
            count=3,
            names=["成員1", "成員2", "成員3"]
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def _create_test_image(self, name_prefix, format='HEIC', color='red', size=(800, 600)):
        """
        創建測試圖片（HEIC 格式）
        
        注意：Pillow 無法直接保存 HEIC 格式，所以我們創建 JPEG 內容但使用 HEIC 的文件名和 content_type
        這模擬了 iPhone 等設備上傳的 HEIC 格式照片
        """
        img = Image.new('RGB', size, color=color)
        img_io = BytesIO()
        img.save(img_io, format='JPEG')  # Pillow 無法保存 HEIC，所以保存為 JPEG
        img_io.seek(0)
        heic_content = img_io.read()
        
        return SimpleUploadedFile(
            name=f'{name_prefix}_photo.HEIC',
            content=heic_content,
            content_type='image/heic'
        )
    
    def _create_route_with_photo_and_checked_members(self, name, grade, photo_file, member_completions, expected_status=status.HTTP_201_CREATED):
        """
        輔助方法：創建帶照片和勾選成員的路線
        
        模擬實際使用場景：
        1. 新增路線
        2. 填入路線名稱、等級、照片，並選取有通過的人員
        3. 點選創建路線
        """
        url = f'/api/rooms/{self.room.id}/routes/'
        
        # 使用FormData格式（因為要上傳照片）
        data = {
            'name': name,
            'grade': grade,
            'member_completions': json.dumps(member_completions),
            'photo': photo_file
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart'
        )
        
        logger.info(f"{name} 創建測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != expected_status:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        return response
    
    def test_create_route_with_photo_and_one_checked_member(self):
        """
        測試：新增路線，填入路線名稱、等級、照片，並選取一個有通過的人員，點選創建路線應該成功
        
        測試步驟：
        1. 新增路線
        2. 填入路線名稱、等級、照片，並選取成員1為已通過
        3. 點選創建路線
        4. 驗證創建成功
        5. 驗證成員1的完成狀態為True
        6. 驗證其他成員的完成狀態為False
        7. 驗證照片上傳成功
        """
        # 創建測試照片
        photo_file = self._create_test_image('route_one_member', color='blue')
        
        # 選取有通過的人員（成員1）
        member_completions = {
            str(self.m1.id): True,  # 成員1已通過
            str(self.m2.id): False,
            str(self.m3.id): False
        }
        
        response = self._create_route_with_photo_and_checked_members(
            '【路線】單成員完成路線',
            'V3',
            photo_file,
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證照片上傳成功（HEIC 格式會被轉換為 JPEG）
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name), 
                       f"照片文件應該存在於存儲中: {route.photo.name}")
        # 驗證 HEIC 格式被轉換為 JPEG
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"HEIC 格式應該被轉換為 JPEG，但文件名是: {route.photo.name}"
        )
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertFalse(score2.is_completed, "成員2應該標記為未完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_photo_and_all_checked_members(self):
        """
        測試：新增路線，填入路線名稱、等級、照片，並選取所有有通過的人員，點選創建路線應該成功
        
        測試步驟：
        1. 新增路線
        2. 填入路線名稱、等級、照片，並選取所有成員為已通過
        3. 點選創建路線
        4. 驗證創建成功
        5. 驗證所有成員的完成狀態為True
        6. 驗證照片上傳成功
        """
        # 創建測試照片
        photo_file = self._create_test_image('route_all_members', color='green')
        
        # 選取所有有通過的人員
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): True
        }
        
        response = self._create_route_with_photo_and_checked_members(
            '【路線】全部完成路線',
            'V4',
            photo_file,
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證照片上傳成功（HEIC 格式會被轉換為 JPEG）
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name), 
                       f"照片文件應該存在於存儲中: {route.photo.name}")
        # 驗證 HEIC 格式被轉換為 JPEG
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"HEIC 格式應該被轉換為 JPEG，但文件名是: {route.photo.name}"
        )
        
        # 驗證所有成員的完成狀態
        for member in [self.m1, self.m2, self.m3]:
            score = Score.objects.get(member=member, route=route)
            self.assertTrue(score.is_completed, f"成員{member.id}應該標記為已完成")
    
    def test_create_route_with_photo_and_partial_checked_members(self):
        """
        測試：新增路線，填入路線名稱、等級、照片，並選取部分有通過的人員，點選創建路線應該成功
        
        測試步驟：
        1. 新增路線
        2. 填入路線名稱、等級、照片，並選取成員1和成員2為已通過
        3. 點選創建路線
        4. 驗證創建成功
        5. 驗證成員1和成員2的完成狀態為True
        6. 驗證成員3的完成狀態為False
        7. 驗證照片上傳成功
        """
        # 創建測試照片
        photo_file = self._create_test_image('route_partial_members', color='orange')
        
        # 選取部分有通過的人員（成員1和成員2）
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        response = self._create_route_with_photo_and_checked_members(
            '【路線】部分完成路線',
            'V5',
            photo_file,
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證照片上傳成功（HEIC 格式會被轉換為 JPEG）
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name), 
                       f"照片文件應該存在於存儲中: {route.photo.name}")
        # 驗證 HEIC 格式被轉換為 JPEG
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"HEIC 格式應該被轉換為 JPEG，但文件名是: {route.photo.name}"
        )
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_photo_and_list_member_completions(self):
        """
        測試：當FormData將member_completions解析為列表時，新增路線並上傳照片應該成功
        
        測試步驟：
        1. 新增路線
        2. 填入路線名稱、等級、照片，並選取有通過的人員（模擬FormData解析為列表的情況）
        3. 點選創建路線
        4. 驗證創建成功
        5. 驗證成員的完成狀態正確
        6. 驗證照片上傳成功
        
        這個測試模擬了Django QueryDict可能將FormData中的值解析為列表的情況
        """
        # 創建測試照片
        photo_file = self._create_test_image('route_list_format', color='purple')
        
        url = f'/api/rooms/{self.room.id}/routes/'
        
        # 選取有通過的人員
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        # 模擬FormData將member_completions解析為列表的情況
        from django.http import QueryDict
        data = QueryDict(mutable=True)
        data['name'] = '【路線】列表格式路線'
        data['grade'] = 'V3'
        data.setlist('member_completions', [json.dumps(member_completions)])  # 設置為列表
        data['photo'] = photo_file
        
        response = self.client.post(
            url,
            data=data,
            format='multipart'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"使用列表格式的member_completions創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證照片上傳成功（HEIC 格式會被轉換為 JPEG）
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name), 
                       f"照片文件應該存在於存儲中: {route.photo.name}")
        # 驗證 HEIC 格式被轉換為 JPEG
        self.assertTrue(
            route.photo.name.lower().endswith(('.jpg', '.jpeg')),
            f"HEIC 格式應該被轉換為 JPEG，但文件名是: {route.photo.name}"
        )
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")

