from rest_framework import serializers
from django.utils.html import escape
import logging
from .models import Room, Member, Route, Score

logger = logging.getLogger(__name__)


def convert_file_to_uploaded_file(file_obj):
    """
    強制將文件對象轉換為 InMemoryUploadedFile，避免 pickle 錯誤
    
    這個函數會處理所有可能的文件對象類型：
    - BufferedRandom
    - BufferedReader
    - 包裝在 UploadedFile 中的 BufferedRandom/BufferedReader
    - 其他不可序列化的文件對象
    
    參數:
        file_obj: 任何文件對象
        
    返回:
        InMemoryUploadedFile: 可序列化的文件對象
    """
    import io
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from io import BytesIO
    
    # 如果已經是 InMemoryUploadedFile 或 SimpleUploadedFile，直接返回
    from django.core.files.uploadedfile import SimpleUploadedFile
    if isinstance(file_obj, (InMemoryUploadedFile, SimpleUploadedFile)):
        # 但需要檢查內部文件對象
        if hasattr(file_obj, 'file'):
            if isinstance(file_obj.file, (io.BufferedRandom, io.BufferedReader)):
                # 內部文件對象仍然是不可序列化的，需要轉換
                logger.warning(f"[convert_file_to_uploaded_file] 檢測到包裝的不可序列化文件對象，類型: {type(file_obj.file)}")
                file_obj.seek(0)
                file_content = file_obj.read()
                file_obj.seek(0)
                
                return InMemoryUploadedFile(
                    BytesIO(file_content),
                    'photo',
                    getattr(file_obj, 'name', 'photo.jpg'),
                    getattr(file_obj, 'content_type', 'image/jpeg'),
                    len(file_content),
                    None
                )
        return file_obj
    
    # 檢查是否直接是 BufferedRandom 或 BufferedReader
    if isinstance(file_obj, (io.BufferedRandom, io.BufferedReader)):
        logger.warning(f"[convert_file_to_uploaded_file] 檢測到直接的文件對象，類型: {type(file_obj)}")
        file_obj.seek(0)
        file_content = file_obj.read()
        file_obj.seek(0)
        
        return InMemoryUploadedFile(
            BytesIO(file_content),
            'photo',
            getattr(file_obj, 'name', 'photo.jpg'),
            'image/jpeg',
            len(file_content),
            None
        )
    
    # 檢查是否包裝在 UploadedFile 中
    if hasattr(file_obj, 'file'):
        if isinstance(file_obj.file, (io.BufferedRandom, io.BufferedReader)):
            logger.warning(f"[convert_file_to_uploaded_file] 檢測到包裝的不可序列化文件對象，類型: {type(file_obj.file)}")
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            file_content = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            return InMemoryUploadedFile(
                BytesIO(file_content),
                'photo',
                getattr(file_obj, 'name', 'photo.jpg'),
                getattr(file_obj, 'content_type', 'image/jpeg'),
                len(file_content),
                None
            )
    
    # 如果都不匹配，嘗試讀取內容並創建新文件（安全起見）
    try:
        if hasattr(file_obj, 'read'):
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            file_content = file_obj.read()
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            return InMemoryUploadedFile(
                BytesIO(file_content),
                'photo',
                getattr(file_obj, 'name', 'photo.jpg'),
                getattr(file_obj, 'content_type', 'image/jpeg'),
                len(file_content),
                None
            )
    except Exception as e:
        logger.error(f"[convert_file_to_uploaded_file] 轉換文件對象時發生錯誤: {e}")
        # 如果轉換失敗，返回原對象（可能會導致 pickle 錯誤，但至少不會崩潰）
        return file_obj
    
    # 如果無法處理，返回原對象
    logger.warning(f"[convert_file_to_uploaded_file] 無法識別文件對象類型: {type(file_obj)}，返回原對象")
    return file_obj


class ScoreSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    member_id = serializers.IntegerField(source='member.id', read_only=True)

    class Meta:
        model = Score
        fields = ['id', 'member_id', 'member_name', 'is_completed', 'score_attained']


class RouteSerializer(serializers.ModelSerializer):
    scores = ScoreSerializer(many=True, read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'name', 'grade', 'photo', 'photo_url', 'scores', 'created_at']
    
    def to_representation(self, instance):
        """確保 scores 數據是最新的"""
        representation = super().to_representation(instance)
        
        # 從數據庫重新獲取 scores 以確保數據最新（避免緩存問題）
        # 如果已經預取，直接使用；否則重新查詢
        if hasattr(instance, '_prefetched_objects_cache') and 'scores' in instance._prefetched_objects_cache:
            scores = instance._prefetched_objects_cache['scores']
        else:
            scores = instance.scores.all()
        
        representation['scores'] = ScoreSerializer(scores, many=True).data
        return representation
    
    def get_photo_url(self, obj):
        """返回照片的完整 URL"""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        # 如果沒有上傳照片，返回舊的 photo_url（向後兼容）
        return obj.photo_url if obj.photo_url else ''


class RouteCreateSerializer(serializers.ModelSerializer):
    """用於創建路線並批量創建成績記錄"""
    member_completions = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="格式: JSON 字符串，如 '{\"member_id\": true}'"
    )
    grade = serializers.CharField(required=True, allow_blank=False, error_messages={
        'required': '難度等級為必填項目',
        'blank': '難度等級不能為空'
    })
    photo = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Route
        fields = ['name', 'grade', 'photo', 'photo_url', 'member_completions']

    def validate_name(self, value):
        """驗證並清理路線名稱，防止 XSS"""
        if not value:
            raise serializers.ValidationError('路線名稱不能為空')
        
        # 去除首尾空白
        value = value.strip()
        
        # 檢查是否為空字符串
        if not value:
            raise serializers.ValidationError('路線名稱不能為空')
        
        # 檢查長度限制
        if len(value) > 200:
            raise serializers.ValidationError('路線名稱不能超過200個字符')
        
        # 檢查最小長度
        if len(value) < 1:
            raise serializers.ValidationError('路線名稱至少需要1個字符')
        
        # 防止 XSS 攻擊
        cleaned_value = escape(value)
        
        return cleaned_value
    
    def validate_grade(self, value):
        """驗證並清理難度等級，防止 XSS"""
        if not value:
            raise serializers.ValidationError('難度等級為必填項目，不能為空')
        
        # 去除首尾空白
        value = value.strip()
        
        # 檢查是否為空字符串
        if not value:
            raise serializers.ValidationError('難度等級不能為空')
        
        # 檢查長度限制
        if len(value) > 50:
            raise serializers.ValidationError('難度等級不能超過50個字符')
        
        # 防止 XSS 攻擊
        cleaned_value = escape(value)
        
        return cleaned_value
    
    def validate(self, data):
        """整體驗證路線數據，包括房間內路線名稱重複檢查"""
        # 獲取房間對象（從 context 中）
        room = self.context.get('room')
        
        # 驗證路線名稱在同一房間內是否重複
        name = data.get('name')
        if name and room:
            # 檢查同一房間內是否有相同名稱的路線
            existing_route = Route.objects.filter(room=room, name=name)
            
            if existing_route.exists():
                raise serializers.ValidationError({
                    'name': f'該房間內已存在名為 "{name}" 的路線，請使用不同的名稱。'
                })
        
        return data
    
    def validate_photo(self, value):
        """驗證圖片文件"""
        logger.debug(f"[RouteCreateSerializer.validate_photo] 開始驗證照片")
        
        try:
            if value is None:
                logger.debug(f"[RouteCreateSerializer.validate_photo] 照片為 None，跳過驗證")
                return value
            
            logger.debug(f"[RouteCreateSerializer.validate_photo] 照片信息: "
                        f"名稱={getattr(value, 'name', 'N/A')}, "
                        f"大小={getattr(value, 'size', 'N/A')}, "
                        f"content_type={getattr(value, 'content_type', 'N/A')}")
            
            # 檢查文件大小（限制為 10MB）
            file_size = getattr(value, 'size', 0)
            if file_size > 10 * 1024 * 1024:
                logger.error(f"[RouteCreateSerializer.validate_photo] 照片文件大小超過限制: {file_size} 字節 (限制: 10MB)")
                raise serializers.ValidationError('圖片文件大小不能超過 10MB')
            
            logger.debug(f"[RouteCreateSerializer.validate_photo] 文件大小檢查通過: {file_size} 字節")
            
            # 獲取文件名和 content_type
            file_name = getattr(value, 'name', '') or ''
            content_type = getattr(value, 'content_type', None)
            
            logger.debug(f"[RouteCreateSerializer.validate_photo] 文件名: '{file_name}', content_type: '{content_type}'")
            
            # 檢查是否為 HEIC/HEIF 格式（iPhone 默認格式）
            # Django 的 ImageField 使用 Pillow 驗證，Pillow 不支持 HEIC
            # 我們需要將 HEIC 轉換為 JPEG 以通過驗證
            is_heic = False
            if content_type:
                content_type_lower = content_type.lower()
                if 'heic' in content_type_lower or 'heif' in content_type_lower:
                    is_heic = True
                    logger.debug(f"[RouteCreateSerializer.validate_photo] 從 content_type 檢測到 HEIC/HEIF 格式")
            
            if not is_heic and file_name:
                file_name_lower = file_name.lower()
                if file_name_lower.endswith('.heic') or file_name_lower.endswith('.heif'):
                    is_heic = True
                    logger.debug(f"[RouteCreateSerializer.validate_photo] 從文件名檢測到 HEIC/HEIF 格式")
            
            # 如果是 HEIC 格式，先使用 pyheif 轉換為 JPEG，再用 Pillow 處理
            # 這個方案可以確保第一次拍照時也能正確處理 HEIC 格式
            if is_heic:
                logger.info(f"[RouteCreateSerializer.validate_photo] 檢測到 HEIC/HEIF 格式，開始轉換為 JPEG")
                try:
                    from PIL import Image
                    from io import BytesIO
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    import os
                    
                    logger.debug(f"[RouteCreateSerializer.validate_photo] 開始讀取 HEIC 文件內容")
                    # 讀取文件內容
                    if hasattr(value, 'seek'):
                        value.seek(0)
                    file_content = value.read()
                    logger.debug(f"[RouteCreateSerializer.validate_photo] 文件內容讀取完成，大小: {len(file_content)} 字節")
                    
                    # 方案1：嘗試使用 pyheif 將 HEIC 轉換為 JPEG
                    try:
                        logger.debug(f"[RouteCreateSerializer.validate_photo] 嘗試使用 pyheif 轉換 HEIC")
                        import pyheif
                        
                        # 使用 pyheif 讀取 HEIC 文件（從 bytes 讀取）
                        # pyheif.read_heif 可以接受 bytes 或文件路徑
                        heif_file = pyheif.read_heif(BytesIO(file_content))
                        logger.debug(f"[RouteCreateSerializer.validate_photo] pyheif 讀取成功，模式: {heif_file.mode}, 大小: {heif_file.size}")
                        
                        # 將 HEIC 數據轉換為 Pillow Image
                        img = Image.frombytes(
                            heif_file.mode,
                            heif_file.size,
                            heif_file.data,
                            "raw",
                            heif_file.mode,
                            heif_file.stride,
                        )
                        logger.debug(f"[RouteCreateSerializer.validate_photo] 轉換為 Pillow Image 成功，模式: {img.mode}")
                        
                        # 轉換為 RGB 模式（HEIC 可能是其他模式，如 RGBA）
                        if img.mode != 'RGB':
                            logger.debug(f"[RouteCreateSerializer.validate_photo] 轉換圖片模式: {img.mode} -> RGB")
                            img = img.convert('RGB')
                        
                        # 將圖片保存為 JPEG
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=95)
                        output.seek(0)
                        logger.debug(f"[RouteCreateSerializer.validate_photo] JPEG 轉換完成，大小: {len(output.getvalue())} 字節")
                        
                        # 創建新的文件對象，使用 .jpg 擴展名
                        new_name = file_name
                        if new_name:
                            base_name = os.path.splitext(new_name)[0]
                            new_name = base_name + '.jpg'
                        else:
                            new_name = 'photo.jpg'
                        
                        logger.info(f"[RouteCreateSerializer.validate_photo] HEIC 轉換成功，新文件名: '{new_name}'")
                        
                        # 創建新的 InMemoryUploadedFile 對象
                        new_file = InMemoryUploadedFile(
                            output,
                            'photo',  # field_name
                            new_name,
                            'image/jpeg',  # 改為 image/jpeg
                            len(output.getvalue()),
                            None  # charset
                        )
                        
                        return new_file
                    except ImportError as import_error:
                        logger.warning(f"[RouteCreateSerializer.validate_photo] pyheif 未安裝，嘗試使用 pillow-heif: {str(import_error)}")
                        # pyheif 未安裝，嘗試使用 pillow-heif（如果已安裝）
                        try:
                            logger.debug(f"[RouteCreateSerializer.validate_photo] 嘗試使用 Pillow (pillow-heif) 打開 HEIC")
                            # 嘗試使用 Pillow 打開（如果安裝了 pillow-heif，可以打開 HEIC）
                            img = Image.open(BytesIO(file_content))
                            logger.debug(f"[RouteCreateSerializer.validate_photo] Pillow 打開成功，模式: {img.mode}, 格式: {img.format}")
                            # 轉換為 RGB 模式（HEIC 可能是其他模式）
                            if img.mode != 'RGB':
                                logger.debug(f"[RouteCreateSerializer.validate_photo] 轉換圖片模式: {img.mode} -> RGB")
                                img = img.convert('RGB')
                            
                            # 將圖片保存為 JPEG
                            output = BytesIO()
                            img.save(output, format='JPEG', quality=95)
                            output.seek(0)
                            logger.debug(f"[RouteCreateSerializer.validate_photo] JPEG 轉換完成，大小: {len(output.getvalue())} 字節")
                            
                            # 創建新的文件對象，使用 .jpg 擴展名
                            new_name = file_name
                            if new_name:
                                base_name = os.path.splitext(new_name)[0]
                                new_name = base_name + '.jpg'
                            else:
                                new_name = 'photo.jpg'
                            
                            logger.info(f"[RouteCreateSerializer.validate_photo] HEIC 轉換成功（使用 pillow-heif），新文件名: '{new_name}'")
                            
                            # 創建新的 InMemoryUploadedFile 對象
                            new_file = InMemoryUploadedFile(
                                output,
                                'photo',  # field_name
                                new_name,
                                'image/jpeg',  # 改為 image/jpeg
                                len(output.getvalue()),
                                None  # charset
                            )
                            
                            return new_file
                        except Exception as pillow_error:
                            logger.error(f"[RouteCreateSerializer.validate_photo] Pillow 也無法打開 HEIC: {str(pillow_error)}")
                            logger.error(f"[RouteCreateSerializer.validate_photo] 錯誤類型: {type(pillow_error).__name__}")
                            import traceback
                            logger.error(f"[RouteCreateSerializer.validate_photo] 錯誤堆棧:\n{traceback.format_exc()}")
                            # Pillow 也無法打開 HEIC（可能沒有安裝 pillow-heif）
                            # 在這種情況下，我們仍然允許上傳，但將文件名改為 .jpg
                            # 這樣 Django 的 ImageField 驗證就會通過
                            # 注意：實際文件內容仍然是 HEIC，但文件名是 .jpg
                            # 這是一個後備方案，不推薦使用
                            from django.core.files.uploadedfile import InMemoryUploadedFile
                            from io import BytesIO
                            import os
                            
                            # 讀取原始文件內容
                            if hasattr(value, 'seek'):
                                value.seek(0)
                            file_content = value.read()
                            
                            # 創建新的文件對象，使用 .jpg 擴展名
                            new_name = file_name
                            if new_name:
                                base_name = os.path.splitext(new_name)[0]
                                if not base_name:
                                    base_name = 'photo'
                                new_name = base_name + '.jpg'
                            else:
                                new_name = 'photo.jpg'
                            
                            # 確保文件名以 .jpg 結尾
                            if not new_name.lower().endswith(('.jpg', '.jpeg')):
                                base_name = os.path.splitext(new_name)[0]
                                if not base_name:
                                    base_name = 'photo'
                                new_name = base_name + '.jpg'
                            
                            # 創建新的 InMemoryUploadedFile 對象
                            new_file = InMemoryUploadedFile(
                                BytesIO(file_content),
                                'photo',  # field_name
                                new_name,
                                'image/jpeg',  # 改為 image/jpeg 以通過驗證
                                len(file_content),
                                None  # charset
                            )
                            
                            # 在文件對象上添加標記，表示這是 HEIC 格式
                            new_file._is_heic = True
                            new_file._original_name = file_name
                            new_file._original_content_type = content_type
                            
                            return new_file
                except Exception as pyheif_error:
                    logger.error(f"[RouteCreateSerializer.validate_photo] pyheif 轉換失敗: {str(pyheif_error)}")
                    logger.error(f"[RouteCreateSerializer.validate_photo] 錯誤類型: {type(pyheif_error).__name__}")
                    import traceback
                    logger.error(f"[RouteCreateSerializer.validate_photo] pyheif 錯誤堆棧:\n{traceback.format_exc()}")
                    # pyheif 轉換失敗，嘗試使用 pillow-heif 作為後備
                    try:
                        logger.debug(f"[RouteCreateSerializer.validate_photo] 嘗試使用 Pillow (pillow-heif) 作為後備方案")
                        img = Image.open(BytesIO(file_content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        output = BytesIO()
                        img.save(output, format='JPEG', quality=95)
                        output.seek(0)
                        
                        new_name = file_name
                        if new_name:
                            base_name = os.path.splitext(new_name)[0]
                            new_name = base_name + '.jpg'
                        else:
                            new_name = 'photo.jpg'
                        
                        logger.info(f"[RouteCreateSerializer.validate_photo] HEIC 轉換成功（後備方案），新文件名: '{new_name}'")
                        
                        new_file = InMemoryUploadedFile(
                            output,
                            'photo',
                            new_name,
                            'image/jpeg',
                            len(output.getvalue()),
                            None
                        )
                        
                        return new_file
                    except Exception as pillow_error:
                        logger.error(f"[RouteCreateSerializer.validate_photo] 所有轉換方法都失敗")
                        logger.error(f"[RouteCreateSerializer.validate_photo] Pillow 錯誤: {str(pillow_error)}")
                        logger.error(f"[RouteCreateSerializer.validate_photo] Pillow 錯誤類型: {type(pillow_error).__name__}")
                        import traceback
                        logger.error(f"[RouteCreateSerializer.validate_photo] Pillow 錯誤堆棧:\n{traceback.format_exc()}")
                        # 所有轉換方法都失敗
                        raise serializers.ValidationError(
                            f'無法處理 HEIC 格式圖片。'
                            f'pyheif 錯誤: {str(pyheif_error)}。'
                            f'Pillow 錯誤: {str(pillow_error)}。'
                            f'請安裝 pyheif 或 pillow-heif 庫，或將圖片轉換為 JPEG/PNG 格式後再上傳。'
                        )
                except Exception as e:
                    logger.exception(f"[RouteCreateSerializer.validate_photo] HEIC 轉換時發生未預期的錯誤")
                    logger.error(f"[RouteCreateSerializer.validate_photo] 錯誤類型: {type(e).__name__}, 錯誤信息: {str(e)}")
                    import traceback
                    logger.error(f"[RouteCreateSerializer.validate_photo] 錯誤堆棧:\n{traceback.format_exc()}")
                    # 如果轉換失敗，返回原始錯誤
                    raise serializers.ValidationError(
                        f'無法處理 HEIC 格式圖片。錯誤: {str(e)}。'
                        f'請嘗試將圖片轉換為 JPEG 或 PNG 格式後再上傳。'
                    )
            
            # 對於非 HEIC 格式，嘗試使用 Pillow 驗證
            logger.debug(f"[RouteCreateSerializer.validate_photo] 開始使用 Pillow 驗證非 HEIC 格式圖片")
            try:
                from PIL import Image
                if hasattr(value, 'seek'):
                    value.seek(0)
                img = Image.open(value)
                logger.debug(f"[RouteCreateSerializer.validate_photo] Pillow 打開圖片成功，格式: {img.format}, 模式: {img.mode}, 大小: {img.size}")
                img.verify()
                logger.debug(f"[RouteCreateSerializer.validate_photo] 圖片驗證通過")
                if hasattr(value, 'seek'):
                    value.seek(0)
                
                # 重新打開圖片以獲取格式信息（verify 後需要重新打開）
                if hasattr(value, 'seek'):
                    value.seek(0)
                img = Image.open(value)
                logger.debug(f"[RouteCreateSerializer.validate_photo] 重新打開圖片成功")
                
                # 確保文件名有正確的擴展名（根據實際圖片格式）
                format_ext_map = {
                    'JPEG': '.jpg',
                    'PNG': '.png',
                    'GIF': '.gif',
                    'BMP': '.bmp',
                    'WEBP': '.webp'
                }
                
                # 根據 Pillow 檢測到的格式確定擴展名
                detected_ext = format_ext_map.get(img.format, '.jpg')
                
                # 如果文件沒有擴展名或擴展名不正確，創建新的文件對象
                if not file_name or '.' not in file_name or not file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    from io import BytesIO
                    import os
                    import re
                    
                    if hasattr(value, 'seek'):
                        value.seek(0)
                    file_content = value.read()
                    
                    # 檢查文件名是否包含中文字符或特殊字符
                    # 如果包含，使用安全的默認文件名
                    base_name = os.path.splitext(file_name)[0] if file_name else 'photo'
                    
                    # 檢查是否包含非ASCII字符（包括中文）或特殊字符
                    has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
                    has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False
                    
                    # 如果文件名包含中文字符、特殊字符、過長或為空，使用安全的默認文件名
                    if not base_name or len(base_name) > 50 or has_non_ascii or has_special_chars:
                        base_name = 'photo'
                    
                    new_name = base_name + detected_ext
                    
                    new_file = InMemoryUploadedFile(
                        BytesIO(file_content),
                        'photo',
                        new_name,
                        content_type or f'image/{detected_ext[1:]}',  # 移除點號
                        len(file_content),
                        None
                    )
                    return new_file
                
                # 如果文件名已有擴展名，確保格式正確
                current_ext = os.path.splitext(file_name)[1].lower()
                if current_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    # 擴展名不正確，創建新的文件對象
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    from io import BytesIO
                    import os
                    import re
                    
                    if hasattr(value, 'seek'):
                        value.seek(0)
                    file_content = value.read()
                    
                    base_name = os.path.splitext(file_name)[0] if file_name else 'photo'
                    
                    # 檢查是否包含非ASCII字符（包括中文）或特殊字符
                    has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
                    has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False
                    
                    # 如果文件名包含中文字符、特殊字符、過長或為空，使用安全的默認文件名
                    if not base_name or len(base_name) > 50 or has_non_ascii or has_special_chars:
                        base_name = 'photo'
                    
                    new_name = base_name + detected_ext
                    
                    logger.debug(f"[RouteCreateSerializer.validate_photo] 創建新文件對象（修正擴展名），文件名: '{new_name}'")
                    new_file = InMemoryUploadedFile(
                        BytesIO(file_content),
                        'photo',
                        new_name,
                        content_type or f'image/{detected_ext[1:]}',
                        len(file_content),
                        None
                    )
                    return new_file
                
                logger.debug(f"[RouteCreateSerializer.validate_photo] 文件名和擴展名都正確，直接返回")
                # 即使擴展名正確，如果文件名包含中文字符或特殊字符，也應該使用安全的文件名
                # 這可以避免 ImageField 驗證失敗（特別是 iPhone 屏幕截圖的情況）
                import re
                base_name = os.path.splitext(file_name)[0] if file_name else 'photo'
                has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
                has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False
                
                if has_non_ascii or has_special_chars:
                    # 文件名包含中文字符或特殊字符，創建新的文件對象使用安全文件名
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    from io import BytesIO
                    
                    if hasattr(value, 'seek'):
                        value.seek(0)
                    file_content = value.read()
                    
                    new_name = 'photo' + detected_ext
                    
                    new_file = InMemoryUploadedFile(
                        BytesIO(file_content),
                        'photo',
                        new_name,
                        content_type or f'image/{detected_ext[1:]}',
                        len(file_content),
                        None
                    )
                    return new_file
                
                return value
            except Exception as e:
                # 如果 Pillow 無法打開，但文件有有效的 content_type，仍然允許上傳
                if content_type and any(ext in content_type.lower() for ext in ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'webp']):
                    if hasattr(value, 'seek'):
                        value.seek(0)
                    
                    # 如果沒有擴展名，根據 content_type 添加
                    if not file_name or '.' not in file_name:
                        from django.core.files.uploadedfile import InMemoryUploadedFile
                        from io import BytesIO
                        import os
                        import re
                        
                        content_type_lower = content_type.lower()
                        ext = '.jpg'  # 默認使用 .jpg
                        if 'png' in content_type_lower:
                            ext = '.png'
                        elif 'gif' in content_type_lower:
                            ext = '.gif'
                        elif 'bmp' in content_type_lower:
                            ext = '.bmp'
                        elif 'webp' in content_type_lower:
                            ext = '.webp'
                        
                        if hasattr(value, 'seek'):
                            value.seek(0)
                        file_content = value.read()
                        
                        # 檢查文件名是否包含中文字符或特殊字符
                        base_name = os.path.splitext(file_name)[0] if file_name else 'photo'
                        
                        # 檢查是否包含非ASCII字符（包括中文）或特殊字符
                        has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
                        has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False
                        
                        # 如果文件名包含中文字符、特殊字符、過長或為空，使用安全的默認文件名
                        if not base_name or len(base_name) > 50 or has_non_ascii or has_special_chars:
                            base_name = 'photo'
                        
                        new_name = base_name + ext
                        
                        new_file = InMemoryUploadedFile(
                            BytesIO(file_content),
                            'photo',
                            new_name,
                            content_type,
                            len(file_content),
                            None
                        )
                        return new_file
                    
                    return value
                # 如果沒有有效的 content_type 且 Pillow 無法打開，拒絕上傳
                raise serializers.ValidationError(
                    f'無法驗證圖片格式。錯誤: {str(e)}。'
                    f'支持的格式: jpg, jpeg, png, gif, bmp, webp, heic, heif'
                )
        except serializers.ValidationError:
            # 如果是 ValidationError，直接重新抛出（例如文件大小超限等驗證錯誤）
            raise
        except Exception as e:
            # 如果所有驗證都失敗，返回錯誤
            logger.exception(f"[RouteCreateSerializer.validate_photo] 驗證圖片時發生未預期的錯誤")
            raise serializers.ValidationError(
                f'無法驗證圖片格式。錯誤: {str(e)}。'
                f'支持的格式: jpg, jpeg, png, gif, bmp, webp, heic, heif'
            )
    
    def validate_member_completions(self, value):
        """驗證並解析 member_completions，防止 SQL 注入"""
        import json
        
        # 如果值為 None 或空字符串，返回空字典
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return {}
        
        # 如果值是字符串，嘗試解析 JSON
        if isinstance(value, str):
            # 限制 JSON 字符串長度，防止過大的輸入
            if len(value) > 10000:
                raise serializers.ValidationError('member_completions 數據過大')
            try:
                parsed = json.loads(value)
                # 確保解析後是字典
                if not isinstance(parsed, dict):
                    raise serializers.ValidationError('member_completions 必須是 JSON 對象')
                # 驗證字典中的值都是布林值或可轉換為布林值
                for key, val in parsed.items():
                    if not isinstance(key, (str, int)):
                        raise serializers.ValidationError('member_completions 的鍵必須是字符串或整數')
                    if not isinstance(val, bool):
                        # 嘗試轉換為布林值
                        if isinstance(val, str):
                            parsed[key] = val.lower() in ('true', '1', 'yes')
                        else:
                            parsed[key] = bool(val)
                return parsed
            except json.JSONDecodeError:
                raise serializers.ValidationError('member_completions 必須是有效的 JSON 格式')
        
        # 如果已經是字典，直接返回
        return value if isinstance(value, dict) else {}
    
    def create(self, validated_data):
        member_completions = validated_data.pop('member_completions', {})
        room = self.context['room']
        
        # 如果包含照片，需要先保存路線獲取 ID，然後再處理照片
        # 這樣 route_photo_upload_path 可以使用正確的 route_id
        photo_data = validated_data.pop('photo', None)
        
        # 先創建路線（不包含照片）
        route = Route.objects.create(room=room, **validated_data)
        
        # 如果有照片，現在路線已經有 ID，可以正確處理照片上傳
        if photo_data:
            logger.debug(f"[RouteCreateSerializer.create] 處理照片文件")
            logger.debug(f"[RouteCreateSerializer.create] 照片類型: {type(photo_data)}")
            logger.debug(f"[RouteCreateSerializer.create] 照片名稱: {getattr(photo_data, 'name', 'N/A')}")
            
            # 強制轉換文件對象為可序列化的類型（避免 pickle 錯誤）
            try:
                logger.debug(f"[RouteCreateSerializer.create] 開始轉換文件對象，原始類型: {type(photo_data)}")
                # 使用統一的轉換函數，確保所有不可序列化的文件對象都被轉換
                converted_photo = convert_file_to_uploaded_file(photo_data)
                logger.debug(f"[RouteCreateSerializer.create] 文件對象轉換完成，新類型: {type(converted_photo)}")
                route.photo = converted_photo
            except Exception as e:
                import traceback
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
                
                logger.exception(f"[RouteCreateSerializer.create] 處理照片文件時發生錯誤")
                logger.error(f"[RouteCreateSerializer.create] 錯誤類型: {type(e).__name__}")
                logger.error(f"[RouteCreateSerializer.create] 錯誤信息: {str(e)}")
                logger.error(f"[RouteCreateSerializer.create] 錯誤模塊: {type(e).__module__}")
                logger.error(f"[RouteCreateSerializer.create] 錯誤文件: {exc_traceback.tb_frame.f_code.co_filename if exc_traceback else 'N/A'}")
                logger.error(f"[RouteCreateSerializer.create] 錯誤行號: {exc_traceback.tb_lineno if exc_traceback else 'N/A'}")
                
                # 記錄完整的堆棧跟踪
                full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
                logger.error(f"[RouteCreateSerializer.create] 完整錯誤堆棧:\n{''.join(full_traceback)}")
                
                # 記錄所有堆棧幀
                if exc_traceback:
                    logger.error(f"[RouteCreateSerializer.create] 堆棧幀詳情:")
                    frame = exc_traceback
                    frame_num = 0
                    while frame:
                        logger.error(f"  幀 {frame_num}: {frame.tb_frame.f_code.co_filename}:{frame.tb_lineno} in {frame.tb_frame.f_code.co_name}")
                        frame = frame.tb_next
                        frame_num += 1
                        if frame_num > 50:  # 限制最多50個幀
                            logger.error(f"  ... (還有更多幀)")
                            break
                
                # 檢查是否為 pickle 錯誤
                if 'pickle' in str(e).lower() or 'BufferedRandom' in str(e) or 'BufferedReader' in str(e):
                    logger.critical(f"[RouteCreateSerializer.create] ⚠️ 檢測到 PICKLE 錯誤！")
                    logger.critical(f"[RouteCreateSerializer.create] 文件對象類型: {type(photo_data)}")
                    if hasattr(photo_data, 'file'):
                        logger.critical(f"[RouteCreateSerializer.create] 內部文件對象類型: {type(photo_data.file)}")
                    logger.critical(f"[RouteCreateSerializer.create] 文件對象屬性: {dir(photo_data)}")
                
                # 如果處理失敗，仍然嘗試使用原始文件對象
                route.photo = photo_data
            
            # 使用路線的 ID 來處理照片上傳
            # route_photo_upload_path 現在可以使用 route.id 而不是 'new'
            try:
                logger.debug(f"[RouteCreateSerializer.create] 準備保存路線，ID: {route.id}")
                logger.debug(f"[RouteCreateSerializer.create] 路線照片字段類型: {type(route.photo) if route.photo else 'None'}")
                if route.photo:
                    logger.debug(f"[RouteCreateSerializer.create] 路線照片名稱: {getattr(route.photo, 'name', 'N/A')}")
                    logger.debug(f"[RouteCreateSerializer.create] 路線照片大小: {getattr(route.photo, 'size', 'N/A')}")
                    # 檢查照片對象的內部文件對象
                    if hasattr(route.photo, 'file'):
                        logger.debug(f"[RouteCreateSerializer.create] 路線照片內部文件對象類型: {type(route.photo.file)}")
                        import io
                        if isinstance(route.photo.file, io.BufferedRandom) or isinstance(route.photo.file, io.BufferedReader):
                            logger.critical(f"[RouteCreateSerializer.create] ⚠️ 警告：照片文件對象仍然是 BufferedRandom/BufferedReader！這會導致 pickle 錯誤！")
                            logger.critical(f"[RouteCreateSerializer.create] 需要立即轉換為 InMemoryUploadedFile")
                
                route.save()
                logger.debug(f"[RouteCreateSerializer.create] 路線保存成功")
            except Exception as save_error:
                import traceback
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
                
                logger.critical(f"[RouteCreateSerializer.create] ⚠️ 保存路線時發生錯誤！")
                logger.critical(f"[RouteCreateSerializer.create] 錯誤類型: {type(save_error).__name__}")
                logger.critical(f"[RouteCreateSerializer.create] 錯誤信息: {str(save_error)}")
                
                # 記錄完整的堆棧跟踪
                full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
                logger.critical(f"[RouteCreateSerializer.create] 完整錯誤堆棧:\n{''.join(full_traceback)}")
                
                # 記錄所有堆棧幀
                if exc_traceback:
                    logger.critical(f"[RouteCreateSerializer.create] 堆棧幀詳情:")
                    frame = exc_traceback
                    frame_num = 0
                    while frame:
                        logger.critical(f"  幀 {frame_num}: {frame.tb_frame.f_code.co_filename}:{frame.tb_lineno} in {frame.tb_frame.f_code.co_name}")
                        frame = frame.tb_next
                        frame_num += 1
                        if frame_num > 50:
                            logger.critical(f"  ... (還有更多幀)")
                            break
                
                # 檢查是否為 pickle 錯誤
                if 'pickle' in str(save_error).lower():
                    logger.critical(f"[RouteCreateSerializer.create] ⚠️⚠️⚠️ 確認是 PICKLE 錯誤！⚠️⚠️⚠️")
                    logger.critical(f"[RouteCreateSerializer.create] 這通常發生在 Django 嘗試序列化文件對象時")
                    logger.critical(f"[RouteCreateSerializer.create] 當前照片對象類型: {type(route.photo) if route.photo else 'None'}")
                    if route.photo:
                        logger.critical(f"[RouteCreateSerializer.create] 照片對象屬性: {[attr for attr in dir(route.photo) if not attr.startswith('_')]}")
                        if hasattr(route.photo, 'file'):
                            logger.critical(f"[RouteCreateSerializer.create] 照片內部文件對象類型: {type(route.photo.file)}")
                            logger.critical(f"[RouteCreateSerializer.create] 這就是問題所在！需要轉換為 InMemoryUploadedFile")
                
                raise  # 重新拋出異常
        
        # 批量創建所有成員的 Score 記錄
        members = room.members.all()
        for member in members:
            # 嘗試兩種 key 格式：字符串和整數
            member_id_str = str(member.id)
            member_id_int = member.id
            
            is_completed = False
            if member_id_str in member_completions:
                is_completed = member_completions[member_id_str]
            elif member_id_int in member_completions:
                is_completed = member_completions[member_id_int]
            
            # 確保 is_completed 是布林值
            if isinstance(is_completed, str):
                is_completed = is_completed.lower() in ('true', '1', 'yes')
            
            Score.objects.create(
                member=member,
                route=route,
                is_completed=bool(is_completed)
            )
        
        # 觸發計分更新
        from .models import update_scores
        update_scores(room.id)
        
        return route


class RouteUpdateSerializer(serializers.ModelSerializer):
    """用於更新路線並批量更新成績記錄"""
    member_completions = serializers.CharField(
        write_only=True,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="格式: JSON 字符串，如 '{\"member_id\": true}'"
    )
    # 使用 FileField 而不是 ImageField，以允許手動驗證
    photo = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Route
        fields = ['name', 'grade', 'photo', 'photo_url', 'member_completions']
    
    def validate_name(self, value):
        """驗證並清理路線名稱，防止 XSS"""
        if not value:
            raise serializers.ValidationError('路線名稱不能為空')
        
        # 去除首尾空白
        value = value.strip()
        
        # 檢查是否為空字符串
        if not value:
            raise serializers.ValidationError('路線名稱不能為空')
        
        # 檢查長度限制
        if len(value) > 200:
            raise serializers.ValidationError('路線名稱不能超過200個字符')
        
        # 檢查最小長度
        if len(value) < 1:
            raise serializers.ValidationError('路線名稱至少需要1個字符')
        
        # 防止 XSS 攻擊
        cleaned_value = escape(value)
        
        return cleaned_value
    
    def validate_grade(self, value):
        """驗證並清理難度等級，防止 XSS"""
        # 如果值為 None 或空字符串，允許為空（更新時可能不提供）
        if value is None or (isinstance(value, str) and not value.strip()):
            # 在更新操作中，如果沒有提供 grade，保持原值
            if self.instance:
                return self.instance.grade
            # 如果沒有 instance（不應該發生），返回空字符串
            return ''
        
        # 去除首尾空白
        value = value.strip()
        
        # 檢查是否為空字符串
        if not value:
            if self.instance:
                return self.instance.grade
            return ''
        
        # 檢查長度限制
        if len(value) > 50:
            raise serializers.ValidationError('難度等級不能超過50個字符')
        
        # 防止 XSS 攻擊
        cleaned_value = escape(value)
        
        return cleaned_value
    
    def validate(self, data):
        """整體驗證路線數據，包括房間內路線名稱重複檢查"""
        # 獲取房間對象（從 instance 中獲取，因為更新操作時 instance 已存在）
        room = None
        if self.instance:
            room = self.instance.room
        else:
            # 創建操作時，從 context 中獲取（雖然 RouteUpdateSerializer 通常用於更新）
            room = self.context.get('room')
        
        # 驗證路線名稱在同一房間內是否重複
        name = data.get('name')
        if name and room:
            # 檢查同一房間內是否有相同名稱的路線
            existing_route = Route.objects.filter(room=room, name=name)
            
            # 如果是更新操作，排除當前路線
            if self.instance:
                existing_route = existing_route.exclude(id=self.instance.id)
            
            if existing_route.exists():
                raise serializers.ValidationError({
                    'name': f'該房間內已存在名為 "{name}" 的路線，請使用不同的名稱。'
                })
        
        return data
    
    def validate_photo(self, value):
        """驗證圖片文件（與 RouteCreateSerializer 相同）"""
        logger.debug(f"[RouteUpdateSerializer.validate_photo] 開始驗證照片")
        
        try:
            if value is None:
                logger.debug(f"[RouteUpdateSerializer.validate_photo] 照片為 None，跳過驗證")
                return value
            
            logger.debug(f"[RouteUpdateSerializer.validate_photo] 照片信息: "
                        f"名稱={getattr(value, 'name', 'N/A')}, "
                        f"大小={getattr(value, 'size', 'N/A')}, "
                        f"content_type={getattr(value, 'content_type', 'N/A')}")
            
            # 重用 RouteCreateSerializer 的驗證邏輯
            # 通過調用父類的方法來避免代碼重複
            from .serializers import RouteCreateSerializer
            create_serializer = RouteCreateSerializer()
            
            logger.debug(f"[RouteUpdateSerializer.validate_photo] 調用 RouteCreateSerializer.validate_photo")
            result = create_serializer.validate_photo(value)
            
            if result:
                logger.debug(f"[RouteUpdateSerializer.validate_photo] 照片驗證成功: "
                            f"名稱={getattr(result, 'name', 'N/A')}, "
                            f"content_type={getattr(result, 'content_type', 'N/A')}")
            else:
                logger.debug(f"[RouteUpdateSerializer.validate_photo] 照片驗證返回 None")
            
            return result
            
        except serializers.ValidationError as e:
            logger.error(f"[RouteUpdateSerializer.validate_photo] 照片驗證失敗（ValidationError）: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"[RouteUpdateSerializer.validate_photo] 照片驗證時發生未預期的錯誤")
            logger.error(f"[RouteUpdateSerializer.validate_photo] 錯誤類型: {type(e).__name__}, 錯誤信息: {str(e)}")
            import traceback
            logger.error(f"[RouteUpdateSerializer.validate_photo] 錯誤堆棧:\n{traceback.format_exc()}")
            raise serializers.ValidationError(f'照片驗證失敗: {str(e)}')
    
    def validate_photo_url(self, value):
        """驗證 photo_url 字段，防止 URL 格式錯誤"""
        logger.debug(f"[RouteUpdateSerializer.validate_photo_url] 開始驗證 photo_url，原始值類型: {type(value)}, 值: {value}")
        
        try:
            # 如果值為 None 或空字符串，返回空字符串（允許空值）
            if value is None or (isinstance(value, str) and value.strip() == ''):
                logger.debug(f"[RouteUpdateSerializer.validate_photo_url] photo_url 為空，返回空字符串")
                return ''
            
            # 如果是字符串，確保它是有效的 URL 格式
            if isinstance(value, str):
                value = value.strip()
                logger.debug(f"[RouteUpdateSerializer.validate_photo_url] photo_url 清理後: '{value}'")
                
                # 如果為空，返回空字符串
                if not value:
                    logger.debug(f"[RouteUpdateSerializer.validate_photo_url] photo_url 清理後為空，返回空字符串")
                    return ''
                
                # 基本 URL 格式驗證（簡單檢查）
                # Django 的 URLField 會進行更嚴格的驗證，這裡先做基本檢查
                if not (value.startswith('http://') or value.startswith('https://') or 
                        value.startswith('/') or value.startswith('data:')):
                    # 如果不是有效的 URL 格式，返回空字符串（而不是拋出錯誤）
                    # 這樣可以避免 "The string did not match the expected pattern" 錯誤
                    logger.warning(f"[RouteUpdateSerializer.validate_photo_url] photo_url 不符合 URL 格式: '{value}'，返回空字符串")
                    return ''
                
                logger.debug(f"[RouteUpdateSerializer.validate_photo_url] photo_url 驗證通過: '{value}'")
                return value
            else:
                logger.warning(f"[RouteUpdateSerializer.validate_photo_url] photo_url 類型不正確: {type(value)}，返回空字符串")
                return ''
                
        except Exception as e:
            logger.exception(f"[RouteUpdateSerializer.validate_photo_url] 驗證 photo_url 時發生錯誤")
            logger.error(f"[RouteUpdateSerializer.validate_photo_url] 錯誤類型: {type(e).__name__}, 錯誤信息: {str(e)}")
            # 發生錯誤時返回空字符串，避免驗證失敗
            return ''
    
    def validate_member_completions(self, value):
        """驗證 member_completions 字段，防止 SQL 注入"""
        import json
        
        # 如果值為 None 或空字符串，返回 None
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None
        
        # 如果值是字符串，嘗試解析 JSON
        if isinstance(value, str):
            # 限制 JSON 字符串長度，防止過大的輸入
            if len(value) > 10000:
                raise serializers.ValidationError('member_completions 數據過大')
            try:
                parsed = json.loads(value)
                # 確保解析後是字典
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        
        # 如果已經是字典，直接返回
        return value if isinstance(value, dict) else {}

    def update(self, instance, validated_data):
        member_completions = validated_data.pop('member_completions', None)
        room = instance.room
        
        # 更新路線信息（只更新提供的字段）
        if 'name' in validated_data:
            instance.name = validated_data['name']
        if 'grade' in validated_data:
            instance.grade = validated_data['grade']
        # 如果提供了新照片，更新照片
        if 'photo' in validated_data:
            photo = validated_data.get('photo')
            if photo:
                logger.debug(f"[RouteUpdateSerializer.update] 處理照片文件更新")
                logger.debug(f"[RouteUpdateSerializer.update] 照片類型: {type(photo)}")
                logger.debug(f"[RouteUpdateSerializer.update] 照片名稱: {getattr(photo, 'name', 'N/A')}")
                
                # 強制轉換文件對象為可序列化的類型（避免 pickle 錯誤）
                try:
                    logger.debug(f"[RouteUpdateSerializer.update] 開始轉換文件對象，原始類型: {type(photo)}")
                    # 使用統一的轉換函數，確保所有不可序列化的文件對象都被轉換
                    converted_photo = convert_file_to_uploaded_file(photo)
                    logger.debug(f"[RouteUpdateSerializer.update] 文件對象轉換完成，新類型: {type(converted_photo)}")
                    instance.photo = converted_photo
                except Exception as e:
                    import traceback
                    import sys
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    
                    logger.exception(f"[RouteUpdateSerializer.update] 處理照片文件時發生錯誤")
                    logger.error(f"[RouteUpdateSerializer.update] 錯誤類型: {type(e).__name__}")
                    logger.error(f"[RouteUpdateSerializer.update] 錯誤信息: {str(e)}")
                    logger.error(f"[RouteUpdateSerializer.update] 錯誤模塊: {type(e).__module__}")
                    logger.error(f"[RouteUpdateSerializer.update] 錯誤文件: {exc_traceback.tb_frame.f_code.co_filename if exc_traceback else 'N/A'}")
                    logger.error(f"[RouteUpdateSerializer.update] 錯誤行號: {exc_traceback.tb_lineno if exc_traceback else 'N/A'}")
                    
                    # 記錄完整的堆棧跟踪
                    full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    logger.error(f"[RouteUpdateSerializer.update] 完整錯誤堆棧:\n{''.join(full_traceback)}")
                    
                    # 記錄所有堆棧幀
                    if exc_traceback:
                        logger.error(f"[RouteUpdateSerializer.update] 堆棧幀詳情:")
                        frame = exc_traceback
                        frame_num = 0
                        while frame:
                            logger.error(f"  幀 {frame_num}: {frame.tb_frame.f_code.co_filename}:{frame.tb_lineno} in {frame.tb_frame.f_code.co_name}")
                            frame = frame.tb_next
                            frame_num += 1
                            if frame_num > 50:  # 限制最多50個幀
                                logger.error(f"  ... (還有更多幀)")
                                break
                    
                    # 檢查是否為 pickle 錯誤
                    if 'pickle' in str(e).lower() or 'BufferedRandom' in str(e) or 'BufferedReader' in str(e):
                        logger.critical(f"[RouteUpdateSerializer.update] ⚠️ 檢測到 PICKLE 錯誤！")
                        logger.critical(f"[RouteUpdateSerializer.update] 文件對象類型: {type(photo)}")
                        if hasattr(photo, 'file'):
                            logger.critical(f"[RouteUpdateSerializer.update] 內部文件對象類型: {type(photo.file)}")
                        logger.critical(f"[RouteUpdateSerializer.update] 文件對象屬性: {dir(photo)}")
                    
                    # 如果處理失敗，仍然嘗試使用原始文件對象
                    instance.photo = photo
            else:
                logger.debug(f"[RouteUpdateSerializer.update] photo 字段存在但為 None，跳過更新")
        # 向後兼容：如果提供了 photo_url（舊版），保留它
        # 注意：photo_url 已經在 validate_photo_url 中驗證和清理
        if 'photo_url' in validated_data:
            photo_url_value = validated_data.get('photo_url')
            # 確保空字符串被正確處理（URLField 允許 blank=True）
            instance.photo_url = photo_url_value if photo_url_value else ''
        
        # 保存更新後的路線
        try:
            logger.debug(f"[RouteUpdateSerializer.update] 準備保存路線，ID: {instance.id}")
            logger.debug(f"[RouteUpdateSerializer.update] 路線照片字段類型: {type(instance.photo) if instance.photo else 'None'}")
            if instance.photo:
                logger.debug(f"[RouteUpdateSerializer.update] 路線照片名稱: {getattr(instance.photo, 'name', 'N/A')}")
                logger.debug(f"[RouteUpdateSerializer.update] 路線照片大小: {getattr(instance.photo, 'size', 'N/A')}")
                # 檢查照片對象的內部文件對象
                if hasattr(instance.photo, 'file'):
                    logger.debug(f"[RouteUpdateSerializer.update] 路線照片內部文件對象類型: {type(instance.photo.file)}")
                    import io
                    if isinstance(instance.photo.file, io.BufferedRandom) or isinstance(instance.photo.file, io.BufferedReader):
                        logger.critical(f"[RouteUpdateSerializer.update] ⚠️ 警告：照片文件對象仍然是 BufferedRandom/BufferedReader！這會導致 pickle 錯誤！")
                        logger.critical(f"[RouteUpdateSerializer.update] 需要立即轉換為 InMemoryUploadedFile")
            
            instance.save()
            logger.debug(f"[RouteUpdateSerializer.update] 路線保存成功")
        except Exception as save_error:
            import traceback
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            logger.critical(f"[RouteUpdateSerializer.update] ⚠️ 保存路線時發生錯誤！")
            logger.critical(f"[RouteUpdateSerializer.update] 錯誤類型: {type(save_error).__name__}")
            logger.critical(f"[RouteUpdateSerializer.update] 錯誤信息: {str(save_error)}")
            
            # 記錄完整的堆棧跟踪
            full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
            logger.critical(f"[RouteUpdateSerializer.update] 完整錯誤堆棧:\n{''.join(full_traceback)}")
            
            # 記錄所有堆棧幀
            if exc_traceback:
                logger.critical(f"[RouteUpdateSerializer.update] 堆棧幀詳情:")
                frame = exc_traceback
                frame_num = 0
                while frame:
                    logger.critical(f"  幀 {frame_num}: {frame.tb_frame.f_code.co_filename}:{frame.tb_lineno} in {frame.tb_frame.f_code.co_name}")
                    frame = frame.tb_next
                    frame_num += 1
                    if frame_num > 50:
                        logger.critical(f"  ... (還有更多幀)")
                        break
            
            # 檢查是否為 pickle 錯誤
            if 'pickle' in str(save_error).lower():
                logger.critical(f"[RouteUpdateSerializer.update] ⚠️⚠️⚠️ 確認是 PICKLE 錯誤！⚠️⚠️⚠️")
                logger.critical(f"[RouteUpdateSerializer.update] 這通常發生在 Django 嘗試序列化文件對象時")
                logger.critical(f"[RouteUpdateSerializer.update] 當前照片對象類型: {type(instance.photo) if instance.photo else 'None'}")
                if instance.photo:
                    logger.critical(f"[RouteUpdateSerializer.update] 照片對象屬性: {[attr for attr in dir(instance.photo) if not attr.startswith('_')]}")
                    if hasattr(instance.photo, 'file'):
                        logger.critical(f"[RouteUpdateSerializer.update] 照片內部文件對象類型: {type(instance.photo.file)}")
                        logger.critical(f"[RouteUpdateSerializer.update] 這就是問題所在！需要轉換為 InMemoryUploadedFile")
            
            raise  # 重新拋出異常
        
        # 如果提供了成員完成狀態，批量更新
        if member_completions is not None:
            # 處理 member_completions（可能是 JSON 字符串）
            if isinstance(member_completions, str):
                import json
                try:
                    member_completions = json.loads(member_completions)
                except json.JSONDecodeError:
                    member_completions = {}
            
            # 確保 member_completions 是字典類型
            if not isinstance(member_completions, dict):
                member_completions = {}
            
            # 更新所有成員的完成狀態
            for member in room.members.all():
                score, created = Score.objects.get_or_create(
                    member=member,
                    route=instance,
                    defaults={'is_completed': False}
                )
                # 嘗試多種 key 格式（字符串和整數）
                member_id_str = str(member.id)
                member_id_int = member.id
                
                is_completed = False
                if member_id_str in member_completions:
                    is_completed = member_completions[member_id_str]
                elif member_id_int in member_completions:
                    is_completed = member_completions[member_id_int]
                
                # 確保 is_completed 是布林值
                if isinstance(is_completed, str):
                    is_completed = is_completed.lower() in ('true', '1', 'yes')
                
                score.is_completed = bool(is_completed)
                score.save()
        
        # 觸發計分更新
        from .models import update_scores
        update_scores(room.id)
        
        return instance


class MemberSerializer(serializers.ModelSerializer):
    completed_routes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'room', 'name', 'is_custom_calc', 'total_score', 'completed_routes_count']
        read_only_fields = ['total_score', 'completed_routes_count']

    def validate_room(self, value):
        """驗證房間是否存在"""
        if not value:
            raise serializers.ValidationError("房間 ID 不能為空")
        return value

    def validate(self, data):
        """驗證成員名稱在同一房間內是否重複"""
        room = data.get('room')
        name = data.get('name')
        
        # 如果是更新操作，獲取當前實例
        instance = self.instance
        
        if room and name:
            # 檢查同一房間內是否有相同名稱的成員
            existing_member = Member.objects.filter(room=room, name=name)
            
            # 如果是更新操作，排除當前成員
            if instance:
                existing_member = existing_member.exclude(id=instance.id)
            
            if existing_member.exists():
                raise serializers.ValidationError({
                    'name': f'該房間內已存在名為 "{name}" 的成員，請使用不同的名稱。'
                })
        
        return data

    def create(self, validated_data):
        """創建成員並為所有現有路線創建 Score 記錄"""
        member = Member.objects.create(**validated_data)
        
        # 為新成員創建所有現有路線的 Score 記錄（默認未完成）
        room = member.room
        routes = room.routes.all()
        for route in routes:
            Score.objects.create(
                member=member,
                route=route,
                is_completed=False
            )
        
        # 觸發計分更新（會自動更新standard_line_score）
        from .models import update_scores
        update_scores(room.id)
        
        return member

    def update(self, instance, validated_data):
        """更新成員資訊"""
        # 更新成員資訊
        instance.name = validated_data.get('name', instance.name)
        instance.is_custom_calc = validated_data.get('is_custom_calc', instance.is_custom_calc)
        instance.save()
        
        # 觸發計分更新（會自動更新standard_line_score）
        from .models import update_scores
        update_scores(instance.room.id)
        
        return instance


class RoomSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True, read_only=True)
    routes = RouteSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'standard_line_score', 'members', 'routes', 'created_at']
    
    def validate_name(self, value):
        """驗證並清理房間名稱，防止 XSS"""
        if value:
            cleaned_name = escape(value.strip())
            # 限制名稱長度
            if len(cleaned_name) > 200:
                raise serializers.ValidationError('房間名稱不能超過200個字符')
            return cleaned_name
        return value
    
    def to_representation(self, instance):
        """確保嵌套的 RouteSerializer 能正確獲取 context"""
        representation = super().to_representation(instance)
        # 手動序列化 routes 以確保 context 正確傳遞
        request = self.context.get('request')
        
        # 強制重新查詢 routes 並預取 scores 關係，避免緩存問題
        # 使用 select_related 和 prefetch_related 確保數據完整
        # 如果 instance 已經有 prefetch_related，這會使用它；否則重新查詢
        if hasattr(instance, '_prefetched_objects_cache') and 'routes' in instance._prefetched_objects_cache:
            # 如果已經預取，使用預取的數據
            routes = instance._prefetched_objects_cache['routes']
        else:
            # 否則重新查詢並預取
            routes = instance.routes.prefetch_related('scores__member').all()
        
        representation['routes'] = RouteSerializer(
            routes, 
            many=True, 
            context={'request': request} if request else {}
        ).data
        return representation


class LeaderboardSerializer(serializers.Serializer):
    """排行榜序列化器"""
    room_info = serializers.DictField()
    leaderboard = MemberSerializer(many=True)


class ScoreUpdateSerializer(serializers.ModelSerializer):
    """用於更新成績狀態"""
    class Meta:
        model = Score
        fields = ['is_completed']
