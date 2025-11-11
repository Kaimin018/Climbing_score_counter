"""
Django 管理命令：清理未使用的路線照片

此命令會掃描 media/route_photos/ 目錄下的所有照片文件，
檢查是否有對應的路線記錄。如果沒有對應的路線 mapping，
則刪除該照片文件。

使用方法：
    python manage.py cleanup_unused_photos
    
可選參數：
    --dry-run: 只顯示將要刪除的文件，不實際刪除
    --verbose: 顯示詳細信息
"""

import os
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.storage import default_storage
from scoring.models import Route

logger = logging.getLogger('scoring')


class Command(BaseCommand):
    help = '清理 media/route_photos/ 目錄下沒有對應路線記錄的照片文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示將要刪除的文件，不實際刪除',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細信息',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('開始清理未使用的路線照片...'))
        
        # 獲取 media 目錄路徑
        media_root = Path(settings.MEDIA_ROOT)
        route_photos_dir = media_root / 'route_photos'
        
        # 檢查目錄是否存在
        if not route_photos_dir.exists():
            self.stdout.write(self.style.WARNING(f'目錄不存在: {route_photos_dir}'))
            return
        
        # 獲取所有路線使用的照片路徑
        routes_with_photos = Route.objects.exclude(photo='').exclude(photo__isnull=True)
        used_photo_paths = set()
        used_photo_filenames = set()
        
        for route in routes_with_photos:
            if route.photo:
                # 獲取照片的相對路徑（相對於 MEDIA_ROOT）
                photo_path = route.photo.name
                used_photo_paths.add(photo_path)
                
                # 添加文件名（用於匹配）
                photo_filename = os.path.basename(photo_path)
                used_photo_filenames.add(photo_filename)
                
                # 同時添加完整路徑（用於比較）
                try:
                    if default_storage.exists(photo_path):
                        full_path = default_storage.path(photo_path)
                        used_photo_paths.add(str(full_path))
                        # 也添加完整路徑的文件名
                        used_photo_filenames.add(os.path.basename(full_path))
                except (AttributeError, NotImplementedError):
                    # 如果不支持 path() 方法，跳過
                    pass
        
        if verbose:
            self.stdout.write(f'找到 {routes_with_photos.count()} 個路線有照片')
            self.stdout.write(f'正在使用的照片路徑: {len(used_photo_paths)} 個')
        
        # 掃描 route_photos 目錄下的所有文件
        deleted_count = 0
        deleted_size = 0
        error_count = 0
        
        try:
            # 使用 default_storage 來遍歷文件（支持不同的存儲後端）
            if default_storage.exists('route_photos'):
                # 獲取所有文件
                all_files = []
                try:
                    # 嘗試使用 listdir（適用於本地文件系統）
                    dir_path = default_storage.path('route_photos')
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = Path(root) / file
                            relative_path = file_path.relative_to(media_root)
                            all_files.append((str(file_path), str(relative_path)))
                except (AttributeError, NotImplementedError):
                    # 如果不支持 path() 方法（如 S3），使用其他方法
                    # 這裡簡化處理，只處理本地文件系統
                    self.stdout.write(self.style.ERROR('不支持的存儲後端，僅支持本地文件系統'))
                    return
                
                for file_path, relative_path in all_files:
                    file_path_obj = Path(file_path)
                    
                    # 跳過目錄
                    if not file_path_obj.is_file():
                        continue
                    
                    # 檢查文件是否被使用
                    is_used = False
                    filename = file_path_obj.name
                    
                    # 方法1: 檢查相對路徑是否在已使用的路徑中
                    if relative_path in used_photo_paths:
                        is_used = True
                    
                    # 方法2: 檢查完整路徑是否在已使用的路徑中
                    if not is_used and str(file_path) in used_photo_paths:
                        is_used = True
                    
                    # 方法3: 檢查文件名是否匹配任何路線的照片（最可靠的方法）
                    if not is_used and filename in used_photo_filenames:
                        is_used = True
                    
                    # 方法4: 檢查路徑是否包含文件名（處理路徑差異）
                    if not is_used:
                        for used_path in used_photo_paths:
                            if used_path.endswith(filename) or filename in used_path:
                                is_used = True
                                break
                    
                    if not is_used:
                        # 文件未被使用，準備刪除
                        try:
                            file_size = file_path_obj.stat().st_size
                            
                            if dry_run:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'[DRY RUN] 將刪除: {relative_path} ({self._format_size(file_size)})'
                                    )
                                )
                            else:
                                # 實際刪除文件
                                file_path_obj.unlink()
                                deleted_count += 1
                                deleted_size += file_size
                                
                                if verbose:
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'已刪除: {relative_path} ({self._format_size(file_size)})'
                                        )
                                    )
                        except Exception as e:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'刪除文件失敗 {relative_path}: {str(e)}'
                                )
                            )
                            logger.error(f'刪除文件失敗 {relative_path}: {str(e)}', exc_info=True)
                    elif verbose:
                        self.stdout.write(f'保留: {relative_path} (正在使用)')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'掃描目錄時發生錯誤: {str(e)}')
            )
            logger.error(f'掃描目錄時發生錯誤: {str(e)}', exc_info=True)
            return
        
        # 顯示結果
        self.stdout.write('')
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] 將刪除 {deleted_count} 個文件，總大小: {self._format_size(deleted_size)}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'清理完成！刪除了 {deleted_count} 個未使用的照片文件，'
                    f'釋放空間: {self._format_size(deleted_size)}'
                )
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'刪除過程中發生 {error_count} 個錯誤')
            )
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return '0 B'
        
        size_names = ['B', 'KB', 'MB', 'GB']
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f'{size:.2f} {size_names[i]}'

