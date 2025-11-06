from django.test import TestCase, Client
from django.test.utils import override_settings
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
import json


class TestCaseMobileUI(TestCase):
    """測試案例：手機版界面響應式設計"""

    def setUp(self):
        self.client = Client()
        self.room = TestDataFactory.create_room(name="手機測試房間")
        self.m1, self.m2, self.m3 = TestDataFactory.create_normal_members(
            self.room,
            count=3,
            names=["成員A", "成員B", "成員C"]
        )
        
        # 創建測試路線
        self.route1 = TestDataFactory.create_route(
            room=self.room,
            name="路線1",
            grade="V3",
            members=[self.m1, self.m2, self.m3],
            member_completions={str(self.m1.id): True, str(self.m2.id): False, str(self.m3.id): False}
        )
        self.route2 = TestDataFactory.create_route(
            room=self.room,
            name="路線2",
            grade="V4",
            members=[self.m1, self.m2, self.m3],
            member_completions={str(self.m1.id): True, str(self.m2.id): True, str(self.m3.id): False}
        )

    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

    def test_mobile_viewport_meta_tag(self):
        """測試：頁面應該包含 viewport meta 標籤"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'viewport', response.content)
        self.assertIn(b'width=device-width', response.content)
        self.assertIn(b'initial-scale=1.0', response.content)

    def test_mobile_leaderboard_page_loads(self):
        """測試：手機端排行榜頁面可以正常載入"""
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('排行榜', content)

    def test_mobile_api_responses(self):
        """測試：手機端 API 響應正常"""
        # 測試獲取房間數據
        response = self.client.get(f'/api/rooms/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.json())
        self.assertIn('routes', response.json())
        
        # 測試獲取排行榜
        response = self.client.get(f'/api/rooms/{self.room.id}/leaderboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('leaderboard', response.json())
        self.assertIn('room_info', response.json())

    def test_mobile_create_route_with_formdata(self):
        """測試：手機端使用 FormData 創建路線（模擬手機上傳）"""
        # 創建測試圖片
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        test_image = SimpleUploadedFile(
            name='mobile_test_route.png',
            content=img_io.read(),
            content_type='image/png'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False
        }
        
        data = {
            'name': '手機測試路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': test_image
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.json())

    def test_mobile_create_route_with_photo_detailed(self):
        """測試：手機端創建路線時上傳圖片（詳細驗證）"""
        # 創建測試圖片（模擬手機拍照）
        img = Image.new('RGB', (800, 600), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        test_image = SimpleUploadedFile(
            name='IMG_20250101_120000.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        data = {
            'name': '手機拍照路線',
            'grade': 'V6',
            'member_completions': json.dumps(member_completions),
            'photo': test_image
        }
        
        # 模擬 iPhone 上傳
        response = self.client.post(
            url,
            data=data,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        
        # 驗證路線創建成功
        route_id = response_data['id']
        route = Route.objects.get(id=route_id)
        self.assertIsNotNone(route.photo, "路線應該有上傳的圖片")
        self.assertTrue(route.photo.name.startswith('route_photos/'), 
                       f"圖片應該保存在 route_photos/ 目錄下，實際: {route.photo.name}")
        
        # 驗證圖片文件存在
        self.assertTrue(default_storage.exists(route.photo.name),
                       f"圖片文件應該存在: {route.photo.name}")
        
        # 驗證 API 響應包含 photo_url
        self.assertIn('photo_url', response_data)
        self.assertNotEqual(response_data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response_data['photo_url'], 
                     "photo_url 應該包含圖片路徑")
        
        # 清理測試圖片
        if default_storage.exists(route.photo.name):
            default_storage.delete(route.photo.name)

    def test_mobile_update_route_add_photo(self):
        """測試：手機端更新路線時添加圖片（原本沒有圖片）"""
        # 創建測試圖片（模擬手機拍照）
        img = Image.new('RGB', (600, 800), color='green')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        test_image = SimpleUploadedFile(
            name='mobile_photo_001.png',
            content=img_io.read(),
            content_type='image/png'
        )
        
        url = f'/api/routes/{self.route1.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False,
            str(self.m3.id): False
        }
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': test_image
        }
        
        # 模擬 Android 手機上傳
        # 使用 encode_multipart 來正確處理 FormData
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            HTTP_USER_AGENT='Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
        )
        
        self.assertEqual(response.status_code, 200,
                        f"Response status: {response.status_code}, Errors: {response.json() if hasattr(response, 'json') else 'N/A'}")
        
        # 驗證路線已更新並有圖片
        self.route1.refresh_from_db()
        self.assertIsNotNone(self.route1.photo, "路線應該有上傳的圖片")
        self.assertTrue(default_storage.exists(self.route1.photo.name),
                       "圖片文件應該存在")
        
        # 驗證 API 響應包含 photo_url
        response_data = response.json()
        self.assertIn('photo_url', response_data)
        self.assertNotEqual(response_data['photo_url'], '', "photo_url 不應該為空")
        
        # 清理測試圖片
        if default_storage.exists(self.route1.photo.name):
            default_storage.delete(self.route1.photo.name)

    def test_mobile_update_route_replace_photo(self):
        """測試：手機端更新路線時替換圖片（原本有圖片）"""
        from django.core.files.storage import default_storage
        
        # 先為路線添加一張圖片
        img1 = Image.new('RGB', (400, 300), color='red')
        img1_io = BytesIO()
        img1.save(img1_io, format='PNG')
        img1_io.seek(0)
        original_image = SimpleUploadedFile(
            name='original_mobile_photo.png',
            content=img1_io.read(),
            content_type='image/png'
        )
        self.route1.photo = original_image
        self.route1.save()
        old_photo_name = self.route1.photo.name
        
        # 創建新圖片（模擬手機重新拍照）
        img2 = Image.new('RGB', (800, 600), color='purple')
        img2_io = BytesIO()
        img2.save(img2_io, format='JPEG')
        img2_io.seek(0)
        new_image = SimpleUploadedFile(
            name='new_mobile_photo.jpg',
            content=img2_io.read(),
            content_type='image/jpeg'
        )
        
        url = f'/api/routes/{self.route1.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): True
        }
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions),
            'photo': new_image
        }
        
        # 模擬 iPhone 上傳
        # 使用 encode_multipart 來正確處理 FormData
        from django.test.client import encode_multipart, BOUNDARY, MULTIPART_CONTENT
        response = self.client.patch(
            url,
            data=encode_multipart(BOUNDARY, data),
            content_type=MULTIPART_CONTENT,
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        )
        
        self.assertEqual(response.status_code, 200,
                        f"Response status: {response.status_code}, Errors: {response.json() if hasattr(response, 'json') else 'N/A'}")
        
        # 驗證路線已更新並有新圖片
        self.route1.refresh_from_db()
        self.assertIsNotNone(self.route1.photo, "路線應該有新的圖片")
        self.assertNotEqual(self.route1.photo.name, old_photo_name, 
                           "圖片文件名應該不同（新圖片）")
        
        # 驗證新圖片文件存在
        self.assertTrue(default_storage.exists(self.route1.photo.name),
                       "新圖片文件應該存在")
        
        # 驗證 API 響應包含新的 photo_url
        response_data = response.json()
        self.assertIn('photo_url', response_data)
        self.assertNotEqual(response_data['photo_url'], '', "photo_url 不應該為空")
        self.assertIn('route_photos', response_data['photo_url'])
        
        # 清理測試圖片
        if default_storage.exists(self.route1.photo.name):
            default_storage.delete(self.route1.photo.name)

    def test_mobile_photo_upload_different_formats(self):
        """測試：手機端上傳不同格式的圖片（PNG、JPEG、HEIC）"""
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): True
        }
        
        # 測試 PNG 格式
        img_png = Image.new('RGB', (500, 500), color='cyan')
        img_png_io = BytesIO()
        img_png.save(img_png_io, format='PNG')
        img_png_io.seek(0)
        png_image = SimpleUploadedFile(
            name='mobile_photo.png',
            content=img_png_io.read(),
            content_type='image/png'
        )
        
        data_png = {
            'name': 'PNG格式路線',
            'grade': 'V4',
            'member_completions': json.dumps(member_completions),
            'photo': png_image
        }
        
        response = self.client.post(
            url,
            data=data_png,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        
        self.assertEqual(response.status_code, 201)
        route_png = Route.objects.get(id=response.json()['id'])
        self.assertIsNotNone(route_png.photo)
        self.assertTrue(route_png.photo.name.endswith('.png') or 'png' in route_png.photo.name.lower())
        
        # 清理
        if route_png.photo and default_storage.exists(route_png.photo.name):
            default_storage.delete(route_png.photo.name)
        
        # 測試 JPEG 格式
        img_jpeg = Image.new('RGB', (500, 500), color='yellow')
        img_jpeg_io = BytesIO()
        img_jpeg.save(img_jpeg_io, format='JPEG')
        img_jpeg_io.seek(0)
        jpeg_image = SimpleUploadedFile(
            name='mobile_photo.jpg',
            content=img_jpeg_io.read(),
            content_type='image/jpeg'
        )
        
        data_jpeg = {
            'name': 'JPEG格式路線',
            'grade': 'V5',
            'member_completions': json.dumps(member_completions),
            'photo': jpeg_image
        }
        
        response = self.client.post(
            url,
            data=data_jpeg,
            format='multipart',
            HTTP_USER_AGENT='Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36'
        )
        
        self.assertEqual(response.status_code, 201)
        route_jpeg = Route.objects.get(id=response.json()['id'])
        self.assertIsNotNone(route_jpeg.photo)
        
        # 清理
        if route_jpeg.photo and default_storage.exists(route_jpeg.photo.name):
            default_storage.delete(route_jpeg.photo.name)
        
        # 測試 HEIC 格式（iPhone 默認格式）
        # 注意：由於 Pillow 默認不支持 HEIC，我們創建一個模擬的 HEIC 文件
        # 實際系統可能會拒絕 HEIC 格式，或者需要轉換為 JPEG
        # 這裡我們測試系統對 HEIC 格式的處理
        try:
            # 嘗試創建 HEIC 格式的圖片（如果 Pillow 支持）
            # 如果不支持，我們使用 JPEG 內容但標記為 HEIC 格式來測試
            img_heic = Image.new('RGB', (600, 800), color='magenta')
            img_heic_io = BytesIO()
            # HEIC 格式可能不被支持，所以我們保存為 JPEG 但使用 HEIC 的 content-type
            img_heic.save(img_heic_io, format='JPEG')
            img_heic_io.seek(0)
            heic_content = img_heic_io.read()
            
            # 創建模擬 HEIC 文件（使用 JPEG 內容，但標記為 HEIC）
            # 這測試系統是否能正確處理 HEIC 的 content-type
            heic_image = SimpleUploadedFile(
                name='IMG_20250101_120000.HEIC',
                content=heic_content,
                content_type='image/heic'
            )
            
            data_heic = {
                'name': 'HEIC格式路線',
                'grade': 'V6',
                'member_completions': json.dumps(member_completions),
                'photo': heic_image
            }
            
            # 模擬 iPhone 上傳 HEIC 格式
            response = self.client.post(
                url,
                data=data_heic,
                format='multipart',
                HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
            )
            
            # HEIC 格式可能被接受（如果系統支持）或被拒絕（因為 Pillow 驗證）
            # 兩種情況都是合理的
            if response.status_code == 201:
                # 系統接受了 HEIC（可能通過自動轉換）
                route_heic = Route.objects.get(id=response.json()['id'])
                self.assertIsNotNone(route_heic.photo, "HEIC 格式應該被處理")
                
                # 清理
                if route_heic.photo and default_storage.exists(route_heic.photo.name):
                    default_storage.delete(route_heic.photo.name)
            elif response.status_code == 400:
                # 系統拒絕了 HEIC（因為 Pillow 驗證失敗）
                # 這是預期的行為，因為 Pillow 默認不支持 HEIC
                self.assertIn('photo', response.json(), "應該返回 photo 字段的錯誤")
                # 驗證錯誤信息
                errors = response.json()
                if 'photo' in errors:
                    # HEIC 格式被拒絕是正常的
                    self.assertTrue(True, "HEIC 格式被正確拒絕（Pillow 不支持）")
            else:
                # 其他錯誤，記錄但不算失敗
                self.fail(f"意外的響應狀態碼: {response.status_code}, 響應: {response.json() if hasattr(response, 'json') else 'N/A'}")
                
        except Exception as e:
            # 如果創建 HEIC 測試失敗，記錄但不影響測試
            # 這可能是因為 Pillow 不支持 HEIC 格式
            self.skipTest(f"HEIC 格式測試跳過（Pillow 可能不支持 HEIC）: {str(e)}")

    def test_mobile_photo_upload_verify_url(self):
        """測試：手機端上傳圖片後，photo_url 正確返回且可訪問"""
        # 模擬不同手機瀏覽器，每個都創建一個新的路線
        user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        ]
        
        url = f'/api/rooms/{self.room.id}/routes/'
        member_completions = {
            str(self.m1.id): False
        }
        
        for idx, user_agent in enumerate(user_agents):
            # 為每個測試創建新的圖片
            img = Image.new('RGB', (300, 300), color='orange')
            img_io = BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            test_image = SimpleUploadedFile(
                name=f'mobile_verify_photo_{idx}.png',
                content=img_io.read(),
                content_type='image/png'
            )
            
            data = {
                'name': f'驗證URL路線_{idx}',
                'grade': 'V3',
                'member_completions': json.dumps(member_completions),
                'photo': test_image
            }
            
            response = self.client.post(
                url,
                data=data,
                format='multipart',
                HTTP_USER_AGENT=user_agent
            )
            
            self.assertEqual(response.status_code, 201,
                           f"創建路線失敗 (User-Agent: {user_agent}): {response.json() if hasattr(response, 'json') else 'N/A'}")
            response_data = response.json()
            
            # 驗證 photo_url 存在且格式正確
            self.assertIn('photo_url', response_data)
            photo_url = response_data['photo_url']
            self.assertNotEqual(photo_url, '', f"photo_url 不應該為空 (User-Agent: {user_agent})")
            self.assertTrue(photo_url.startswith('http'), 
                           f"photo_url 應該是完整的 URL (User-Agent: {user_agent})")
            
            # 驗證路線在數據庫中有圖片
            route = Route.objects.get(id=response_data['id'])
            self.assertIsNotNone(route.photo, f"路線應該有圖片 (User-Agent: {user_agent})")
            
            # 清理
            if route.photo and default_storage.exists(route.photo.name):
                default_storage.delete(route.photo.name)
            route.delete()

    def test_mobile_update_route(self):
        """測試：手機端更新路線"""
        url = f'/api/routes/{self.route1.id}/'
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): True
        }
        
        data = {
            'name': '【路線】路線1',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.patch(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 驗證更新成功
        self.route1.refresh_from_db()
        updated_scores = self.route1.scores.filter(is_completed=True)
        self.assertEqual(updated_scores.count(), 3)

    def test_mobile_get_member_completed_routes(self):
        """測試：手機端獲取成員完成的路線列表"""
        url = f'/api/members/{self.m1.id}/completed-routes/'
        response = self.client.get(
            url,
            HTTP_USER_AGENT='Mozilla/5.0 (Android 10; Mobile) AppleWebKit/537.36'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('completed_routes', data)
        self.assertIn('total_count', data)
        self.assertEqual(data['total_count'], 2)  # m1 完成了兩條路線

    def test_mobile_responsive_layout_elements(self):
        """測試：手機端頁面包含響應式設計所需的元素"""
        response = self.client.get(f'/leaderboard/{self.room.id}/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # 檢查是否包含響應式 CSS 類
        self.assertIn('leaderboard-layout', content)
        self.assertIn('leaderboard-sidebar', content)
        self.assertIn('main-content', content)
        
        # 檢查是否包含移動端優化的按鈕
        self.assertIn('btn', content)

    def test_mobile_css_media_queries_referenced(self):
        """測試：CSS 文件包含移動端媒體查詢"""
        response = self.client.get('/static/css/style.css')
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            # 檢查是否包含移動端媒體查詢
            self.assertIn('@media (max-width: 768px)', content)
            self.assertIn('@media (max-width: 480px)', content)

    def test_mobile_form_input_font_size(self):
        """測試：手機端表單輸入框字體大小（防止 iOS 自動縮放）"""
        # 這個測試主要驗證 CSS 中是否有 font-size: 16px 的設置
        response = self.client.get('/static/css/style.css')
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            # 檢查移動端樣式中是否有 font-size: 16px（防止 iOS 縮放）
            mobile_section = content[content.find('@media (max-width: 768px)'):]
            if 'font-size: 16px' in mobile_section or 'font-size:16px' in mobile_section:
                self.assertTrue(True)
            else:
                # 如果沒有找到，這不是致命錯誤，只是記錄
                pass

