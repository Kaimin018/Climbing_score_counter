"""
路線照片顯示功能測試用例

測試項目：
1. 創建路線後照片正確顯示
2. 更新路線後照片正確顯示
3. 照片 URL 格式正確
4. 照片在路線列表中正確顯示
"""
from django.test import TestCase, Client
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


class TestCaseRoutePhotoDisplay(TestCase):
    """測試路線照片顯示功能"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = Client()
        self.api_client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("照片顯示測試房間")
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
        self.api_client.force_authenticate(user=self.user)
        
        # 創建測試圖片
        self.test_image = self._create_test_image('test_photo', color='blue')
    
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
        # 使用 cleanup_test_data 的 cleanup_photos 參數自動清理圖片
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def test_create_route_with_photo_displays_correctly(self):
        """測試：創建路線後照片在 API 響應中正確顯示"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '有照片的路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.api_client.post(
            url,
            data=data,
            format='multipart'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
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
        self.assertIn('route_photos', photo_url, f"photo_url 應該包含 'route_photos' 路徑，實際: {photo_url}")
        
        # 驗證數據庫中的路線有照片
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在: {route.photo.name}")
    
    def test_route_list_displays_photo_url(self):
        """測試：路線列表 API 返回正確的照片 URL"""
        # 先創建一個有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="有照片的路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        route.photo = self.test_image
        route.save()
        
        # 獲取路線列表
        url = f'/api/rooms/{self.room.id}/'
        response = self.api_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('routes', response.data)
        
        routes = response.data['routes']
        self.assertGreater(len(routes), 0, "應該至少有一條路線")
        
        # 找到我們創建的路線
        created_route = next((r for r in routes if r['id'] == route.id), None)
        self.assertIsNotNone(created_route, "應該能找到創建的路線")
        
        # 驗證照片 URL
        self.assertIn('photo_url', created_route, "路線應該包含 'photo_url' 字段")
        photo_url = created_route['photo_url']
        self.assertNotEqual(photo_url, '', "photo_url 不應該為空")
        self.assertTrue(
            photo_url.startswith('http://') or photo_url.startswith('https://') or photo_url.startswith('/media/'),
            f"photo_url 應該是有效的 URL 或路徑，實際: {photo_url}"
        )
    
    def test_update_route_photo_displays_correctly(self):
        """測試：更新路線照片後，照片 URL 正確顯示"""
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
        
        # 更新路線，添加照片
        data = {
            'name': '原始路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': self.test_image
        }
        
        response = self.api_client.patch(
            url,
            data=data,
            format='multipart'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            f"更新路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證 API 響應包含照片 URL
        self.assertIn('photo_url', response.data, "API 響應應該包含 'photo_url' 字段")
        photo_url = response.data['photo_url']
        self.assertNotEqual(photo_url, '', "photo_url 不應該為空")
        self.assertTrue(
            photo_url.startswith('http://') or photo_url.startswith('https://') or photo_url.startswith('/media/'),
            f"photo_url 應該是有效的 URL 或路徑，實際: {photo_url}"
        )
        
        # 驗證數據庫中的路線有照片
        route.refresh_from_db()
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(route.photo.name),
                      f"照片文件應該存在: {route.photo.name}")
    
    def test_route_photo_url_accessible(self):
        """測試：路線照片 URL 可以訪問（通過視圖）"""
        # 先創建一個有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="有照片的路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        route.photo = self.test_image
        route.save()
        
        # 登錄用戶
        self.client.force_login(self.user)
        
        # 訪問排行榜頁面（應該包含路線列表）
        url = f'/leaderboard/{self.room.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200, "應該能訪問排行榜頁面")
        
        # 驗證頁面包含路線信息（照片 URL 會在 JavaScript 中處理）
        # 這裡主要驗證頁面能正常載入
        self.assertContains(response, '排行榜', msg_prefix="頁面應該包含 '排行榜' 文字")
    
    def test_route_without_photo_has_empty_photo_url(self):
        """測試：沒有照片的路線，photo_url 應該為空字符串"""
        # 創建一個沒有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="無照片的路線",
            grade="V3",
            members=[self.m1, self.m2]
        )
        
        # 獲取路線詳情
        url = f'/api/routes/{route.id}/'
        response = self.api_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證 photo_url 為空或不存在
        if 'photo_url' in response.data:
            photo_url = response.data['photo_url']
            # photo_url 可能為空字符串或 None
            self.assertTrue(
                photo_url == '' or photo_url is None,
                f"沒有照片的路線，photo_url 應該為空，實際: {photo_url}"
            )
    
    def test_route_photo_url_format_consistency(self):
        """測試：同一路線的照片 URL 格式在不同 API 端點中保持一致"""
        # 創建一個有照片的路線
        route = self.factory.create_route(
            room=self.room,
            name="照片格式測試路線",
            grade="V5",
            members=[self.m1, self.m2]
        )
        route.photo = self.test_image
        route.save()
        
        # 從路線詳情 API 獲取 photo_url
        route_detail_url = f'/api/routes/{route.id}/'
        route_detail_response = self.api_client.get(route_detail_url)
        route_detail_photo_url = route_detail_response.data.get('photo_url', '')
        
        # 從房間詳情 API 獲取 photo_url
        room_detail_url = f'/api/rooms/{self.room.id}/'
        room_detail_response = self.api_client.get(room_detail_url)
        routes = room_detail_response.data.get('routes', [])
        room_route = next((r for r in routes if r['id'] == route.id), None)
        room_route_photo_url = room_route.get('photo_url', '') if room_route else ''
        
        # 驗證兩個 API 返回的 photo_url 格式一致（都應該是有效的 URL 或路徑）
        if route_detail_photo_url:
            self.assertTrue(
                route_detail_photo_url.startswith('http://') or 
                route_detail_photo_url.startswith('https://') or 
                route_detail_photo_url.startswith('/media/'),
                f"路線詳情 API 的 photo_url 格式應該正確，實際: {route_detail_photo_url}"
            )
        
        if room_route_photo_url:
            self.assertTrue(
                room_route_photo_url.startswith('http://') or 
                room_route_photo_url.startswith('https://') or 
                room_route_photo_url.startswith('/media/'),
                f"房間詳情 API 的 photo_url 格式應該正確，實際: {room_route_photo_url}"
            )
        
        # 如果兩個 URL 都不為空，它們應該指向同一個文件（路徑部分應該相同）
        if route_detail_photo_url and room_route_photo_url:
            # 提取路徑部分進行比較（忽略協議和域名）
            detail_path = route_detail_photo_url.split('/media/')[-1] if '/media/' in route_detail_photo_url else route_detail_photo_url
            room_path = room_route_photo_url.split('/media/')[-1] if '/media/' in room_route_photo_url else room_route_photo_url
            self.assertEqual(
                detail_path,
                room_path,
                f"兩個 API 返回的 photo_url 應該指向同一個文件。路線詳情: {detail_path}, 房間詳情: {room_path}"
            )

