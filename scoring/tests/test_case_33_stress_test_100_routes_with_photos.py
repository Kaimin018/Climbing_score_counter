"""
壓力測試：連續創建100條路線並每條都附加不同格式的照片

測試項目：
1. 連續創建100條路線
2. 每條路線都附加不同格式的照片（PNG、JPEG、HEIC、GIF、WEBP等）
3. 每條路線都選擇不同的完成成員（隨機選擇）
4. 測試完成後照片要記得刪除
5. 驗證所有路線和照片都正確創建
6. 驗證數據庫一致性
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, cleanup_test_photos
from PIL import Image
from io import BytesIO
import json
import random
import logging

logger = logging.getLogger(__name__)


class TestCaseStressTest100RoutesWithPhotos(TestCase):
    """壓力測試：連續創建100條路線並每條都附加不同格式的照片"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("壓力測試房間")
        
        # 創建10個成員（足夠選擇不同的完成成員組合）
        self.members = self.factory.create_normal_members(
            self.room,
            count=10,
            names=[f"成員{i+1}" for i in range(10)]
        )
        
        # 定義不同的圖片格式配置
        self.image_formats = [
            {'format': 'PNG', 'ext': '.png', 'content_type': 'image/png', 'color': 'red'},
            {'format': 'JPEG', 'ext': '.jpg', 'content_type': 'image/jpeg', 'color': 'blue'},
            {'format': 'JPEG', 'ext': '.jpeg', 'content_type': 'image/jpeg', 'color': 'green'},
            {'format': 'HEIC', 'ext': '.HEIC', 'content_type': 'image/heic', 'color': 'yellow'},
            {'format': 'GIF', 'ext': '.gif', 'content_type': 'image/gif', 'color': 'purple'},
            {'format': 'WEBP', 'ext': '.webp', 'content_type': 'image/webp', 'color': 'orange'},
            {'format': 'PNG', 'ext': '.PNG', 'content_type': 'image/png', 'color': 'cyan'},
            {'format': 'JPEG', 'ext': '.JPG', 'content_type': 'image/jpeg', 'color': 'magenta'},
        ]
        
        # 存儲創建的路線ID，用於清理
        self.created_routes = []
    
    def tearDown(self):
        """測試完成後清理數據和照片"""
        # 先清理照片
        if self.created_routes:
            routes = Route.objects.filter(id__in=self.created_routes)
            cleanup_test_photos(routes=routes)
        
        # 清理測試數據
        cleanup_test_data(room=self.room, cleanup_photos=True)
    
    def _create_test_image(self, format_config, route_index):
        """
        創建測試圖片
        
        Args:
            format_config: 圖片格式配置字典
            route_index: 路線索引（用於生成不同的圖片）
        
        Returns:
            SimpleUploadedFile: 測試圖片文件
        """
        # 根據格式配置創建不同顏色和大小的圖片
        color = format_config['color']
        size = (400 + route_index % 200, 300 + route_index % 150)  # 不同大小
        
        img = Image.new('RGB', size, color=color)
        img_io = BytesIO()
        
        # 根據格式保存圖片
        # 注意：Pillow 無法直接保存 HEIC 格式，所以使用 JPEG 內容但標記為 HEIC
        if format_config['format'] == 'HEIC':
            img.save(img_io, format='JPEG')
        elif format_config['format'] == 'WEBP':
            try:
                img.save(img_io, format='WEBP')
            except Exception:
                # 如果 WEBP 不支持，使用 JPEG
                img.save(img_io, format='JPEG')
        else:
            img.save(img_io, format=format_config['format'])
        
        img_io.seek(0)
        image_content = img_io.read()
        
        # 生成文件名（模擬不同來源的文件名）
        filename_patterns = [
            f'route_{route_index}_photo{format_config["ext"]}',
            f'IMG_{route_index:04d}{format_config["ext"]}',
            f'photo_{route_index}{format_config["ext"]}',
            f'image_{route_index:03d}{format_config["ext"]}',
        ]
        filename = filename_patterns[route_index % len(filename_patterns)]
        
        return SimpleUploadedFile(
            name=filename,
            content=image_content,
            content_type=format_config['content_type']
        )
    
    def _select_random_members(self, route_index):
        """
        為每條路線隨機選擇不同的完成成員
        
        Args:
            route_index: 路線索引（用於生成不同的選擇模式）
        
        Returns:
            dict: 成員完成狀態字典 {member_id: is_completed}
        """
        # 使用 route_index 作為隨機種子，確保每次測試結果一致
        random.seed(route_index)
        
        # 隨機選擇1到5個成員作為完成
        num_completed = random.randint(1, min(5, len(self.members)))
        completed_member_ids = random.sample(
            [m.id for m in self.members],
            num_completed
        )
        
        # 構建成員完成狀態字典
        member_completions = {}
        for member in self.members:
            member_completions[str(member.id)] = member.id in completed_member_ids
        
        return member_completions
    
    def test_stress_create_100_routes_with_different_photo_formats(self):
        """
        壓力測試：連續創建100條路線，每條都附加不同格式的照片
        
        測試步驟：
        1. 循環創建100條路線
        2. 每條路線使用不同的圖片格式（輪換使用）
        3. 每條路線選擇不同的完成成員（隨機選擇）
        4. 驗證每條路線創建成功
        5. 驗證每條路線的照片正確上傳
        6. 驗證數據庫一致性
        7. 測試完成後清理所有照片
        """
        total_routes = 100
        success_count = 0
        failed_routes = []
        
        logger.info(f"開始壓力測試：創建 {total_routes} 條路線")
        
        for i in range(total_routes):
            try:
                # 選擇圖片格式（輪換使用）
                format_config = self.image_formats[i % len(self.image_formats)]
                
                # 創建測試圖片
                test_image = self._create_test_image(format_config, i)
                
                # 選擇完成成員
                member_completions = self._select_random_members(i)
                
                # 準備請求數據
                url = f'/api/rooms/{self.room.id}/routes/'
                data = {
                    'name': f'壓力測試路線{i+1}',
                    'grade': f'V{3 + (i % 8)}',  # 難度等級從V3到V10輪換
                    'member_completions': json.dumps(member_completions),
                    'photo': test_image
                }
                
                # 發送創建路線請求
                response = self.client.post(url, data, format='multipart')
                
                # 驗證響應
                if response.status_code == status.HTTP_201_CREATED:
                    route_id = response.data['id']
                    self.created_routes.append(route_id)
                    
                    # 驗證路線創建成功
                    route = Route.objects.get(id=route_id)
                    self.assertIsNotNone(route, f"路線 {i+1} 應該存在")
                    
                    # 驗證照片上傳成功
                    self.assertIsNotNone(route.photo, f"路線 {i+1} 應該有照片")
                    self.assertTrue(
                        default_storage.exists(route.photo.name),
                        f"路線 {i+1} 的照片文件應該存在: {route.photo.name}"
                    )
                    
                    # 驗證照片文件大小
                    file_size = default_storage.size(route.photo.name)
                    self.assertGreater(
                        file_size, 0,
                        f"路線 {i+1} 的照片文件大小應該大於 0，實際: {file_size} bytes"
                    )
                    
                    # 驗證API響應包含照片相關字段
                    self.assertIn('photo', response.data, f"路線 {i+1} 的API響應應該包含 'photo' 字段")
                    self.assertIn('photo_url', response.data, f"路線 {i+1} 的API響應應該包含 'photo_url' 字段")
                    self.assertNotEqual(
                        response.data['photo_url'], '',
                        f"路線 {i+1} 的 photo_url 不應該為空"
                    )
                    
                    # 驗證完成成員數量正確
                    expected_completed_count = sum(1 for v in member_completions.values() if v)
                    actual_completed_count = Score.objects.filter(
                        route=route,
                        is_completed=True
                    ).count()
                    self.assertEqual(
                        expected_completed_count,
                        actual_completed_count,
                        f"路線 {i+1} 的完成成員數量應該為 {expected_completed_count}，實際為 {actual_completed_count}"
                    )
                    
                    # 驗證所有成員都有成績記錄
                    all_member_ids = {m.id for m in self.members}
                    route_score_member_ids = set(
                        Score.objects.filter(route=route).values_list('member_id', flat=True)
                    )
                    self.assertEqual(
                        all_member_ids,
                        route_score_member_ids,
                        f"路線 {i+1} 應該為所有成員創建成績記錄"
                    )
                    
                    success_count += 1
                    
                    # 每10條路線記錄一次進度
                    if (i + 1) % 10 == 0:
                        logger.info(f"已創建 {i+1}/{total_routes} 條路線")
                
                else:
                    # 記錄失敗的路線
                    error_msg = response.data if hasattr(response, 'data') else response.content
                    failed_routes.append({
                        'index': i + 1,
                        'status_code': response.status_code,
                        'error': str(error_msg)
                    })
                    logger.error(f"路線 {i+1} 創建失敗: {response.status_code}, 錯誤: {error_msg}")
            
            except Exception as e:
                # 記錄異常
                failed_routes.append({
                    'index': i + 1,
                    'status_code': None,
                    'error': str(e)
                })
                logger.error(f"路線 {i+1} 創建時發生異常: {str(e)}", exc_info=True)
        
        # 驗證所有路線都創建成功
        logger.info(f"壓力測試完成：成功創建 {success_count}/{total_routes} 條路線")
        
        if failed_routes:
            logger.error(f"失敗的路線: {failed_routes}")
            self.fail(
                f"有 {len(failed_routes)} 條路線創建失敗。"
                f"成功: {success_count}/{total_routes}, 失敗: {len(failed_routes)}"
            )
        
        self.assertEqual(
            success_count,
            total_routes,
            f"所有 {total_routes} 條路線都應該創建成功，但只有 {success_count} 條成功"
        )
        
        # 驗證數據庫中的路線數量
        db_route_count = Route.objects.filter(room=self.room).count()
        self.assertEqual(
            db_route_count,
            total_routes,
            f"數據庫中應該有 {total_routes} 條路線，實際有 {db_route_count} 條"
        )
        
        # 驗證所有路線都有照片
        routes_with_photos = Route.objects.filter(room=self.room).exclude(photo='').exclude(photo=None)
        self.assertEqual(
            routes_with_photos.count(),
            total_routes,
            f"所有 {total_routes} 條路線都應該有照片，實際有 {routes_with_photos.count()} 條有照片"
        )
        
        # 驗證所有照片文件都存在
        missing_photos = []
        for route in Route.objects.filter(room=self.room):
            if route.photo and route.photo.name:
                if not default_storage.exists(route.photo.name):
                    missing_photos.append(route.id)
        
        if missing_photos:
            self.fail(f"有 {len(missing_photos)} 條路線的照片文件不存在: {missing_photos}")
        
        logger.info("壓力測試通過：所有路線和照片都正確創建")
    
    def test_stress_verify_photo_deletion_after_test(self):
        """
        驗證測試完成後照片是否正確刪除
        
        這個測試確保 tearDown 方法正確清理了所有照片文件
        """
        # 創建幾條測試路線
        test_count = 5
        created_route_ids = []
        
        for i in range(test_count):
            format_config = self.image_formats[i % len(self.image_formats)]
            test_image = self._create_test_image(format_config, i)
            member_completions = self._select_random_members(i)
            
            url = f'/api/rooms/{self.room.id}/routes/'
            data = {
                'name': f'照片刪除測試路線{i+1}',
                'grade': 'V5',
                'member_completions': json.dumps(member_completions),
                'photo': test_image
            }
            
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            route_id = response.data['id']
            created_route_ids.append(route_id)
            self.created_routes.append(route_id)
            
            # 驗證照片已創建
            route = Route.objects.get(id=route_id)
            self.assertIsNotNone(route.photo)
            self.assertTrue(default_storage.exists(route.photo.name))
        
        # 在清理前獲取所有照片路徑（確保獲取最新的路徑）
        routes_to_clean = Route.objects.filter(id__in=created_route_ids)
        photo_paths = []
        for route in routes_to_clean:
            route.refresh_from_db()  # 確保獲取最新的照片路徑
            if route.photo and route.photo.name:
                photo_path = route.photo.name
                photo_paths.append(photo_path)
                # 驗證照片文件在清理前存在
                self.assertTrue(
                    default_storage.exists(photo_path),
                    f"照片文件在清理前應該存在: {photo_path}"
                )
        
        # 手動清理照片（模擬 tearDown）
        deleted_count = cleanup_test_photos(routes=routes_to_clean)
        
        # 驗證刪除的數量
        self.assertGreater(
            deleted_count, 0,
            f"應該至少刪除一些照片文件，實際刪除: {deleted_count}"
        )
        
        # 驗證照片已被刪除（使用之前記錄的路徑）
        for photo_path in photo_paths:
            self.assertFalse(
                default_storage.exists(photo_path),
                f"照片文件應該已被刪除: {photo_path}"
            )
        
        # 再次驗證數據庫中的route對象（重新獲取以確保獲取最新狀態）
        for route_id in created_route_ids:
            route = Route.objects.get(id=route_id)
            route.refresh_from_db()
            # 注意：Django可能不會立即清空photo字段，但文件應該已被刪除
            if route.photo and route.photo.name:
                # 如果字段還有值，驗證文件確實不存在
                photo_path = route.photo.name
                self.assertFalse(
                    default_storage.exists(photo_path),
                    f"路線 {route_id} 的照片文件應該已被刪除: {photo_path}"
                )
        
        logger.info("照片刪除測試通過：所有照片文件都已正確刪除")

