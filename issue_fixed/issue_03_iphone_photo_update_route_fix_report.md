# 工程報告：iPhone 拍照更新路線時發生 "The string did not match the expected pattern" 錯誤（已修復）

**狀態**: ✅ 已修復並驗證  
**修復日期**: 2025-01-07  
**測試結果**: 8/8 測試用例通過

## 問題描述

**症狀**: 在 iPhone 上使用拍照功能更新路線時，系統返回錯誤："更新路線時發生錯誤: The string did not match the expected pattern."

**影響範圍**: 所有使用 iPhone 拍照功能更新路線的使用者。

**錯誤發生時機**: 
- 更新路線時選擇新照片（通過拍照或從圖庫選擇）
- 特別是第一次使用拍照功能時

## 問題流程分析

### 完整流程圖

```
1. 用戶在 iPhone 上打開編輯路線彈窗
   ↓
2. 用戶點擊「選擇照片」按鈕
   ↓
3. iPhone 顯示選項：拍照 / 從圖庫選擇
   ↓
4. 用戶選擇「拍照」
   ↓
5. iPhone 相機打開，用戶拍照
   ↓
6. 照片被選中，前端 JavaScript 處理：
   - 讀取文件對象 (File object)
   - 顯示預覽 (showPhotoPreview)
   - 同步到兩個 input 元素 (routePhotoInput 和 routePhotoFromGallery)
   ↓
7. 用戶點擊「更新路線」按鈕
   ↓
8. 前端構建 FormData：
   - name: 路線名稱
   - grade: 難度等級
   - photo: 照片文件 (File object)
   - member_completions: JSON 字符串
   - csrfmiddlewaretoken: CSRF token
   ↓
9. 發送 PATCH 請求到 /api/routes/{routeId}/
   ↓
10. Django 後端接收請求：
    - RouteUpdateSerializer 處理數據
    - validate_photo() 方法驗證照片
    ↓
11. 照片驗證流程：
    a. 檢查文件大小（限制 10MB）
    b. 獲取文件名和 content_type
    c. 判斷是否為 HEIC 格式：
       - 檢查 content_type 是否包含 'heic' 或 'heif'
       - 檢查文件名是否以 .heic 或 .heif 結尾
    d. 如果是 HEIC 格式：
       - 嘗試使用 pyheif 轉換為 JPEG
       - 如果 pyheif 未安裝，嘗試使用 pillow-heif
       - 如果都失敗，使用後備方案（重命名文件）
    e. 如果不是 HEIC 格式：
       - 使用 Pillow 驗證圖片格式
       - 如果文件沒有擴展名，根據 content_type 添加
   ↓
12. ❌ 錯誤發生點：
    - Django 的 ImageField 在保存前會進行額外驗證
    - 如果文件名或內容不符合 ImageField 的預期模式，會拋出 "The string did not match the expected pattern" 錯誤
```

### 問題根源

**核心問題**: Django 的 `ImageField` 在模型層面會進行額外的驗證，即使序列化器已經處理了文件，模型保存時仍會觸發 Pillow 的驗證。當 iPhone 拍照產生的文件格式或文件名不符合 Pillow 的預期時，就會拋出此錯誤。

**具體原因**:

1. **文件名格式問題**:
   - iPhone 拍照可能產生沒有擴展名的文件
   - 文件名可能包含特殊字符（如空格、Unicode 字符）
   - 即使序列化器已經處理，模型保存時 ImageField 仍會驗證原始文件名

2. **文件內容驗證**:
   - ImageField 使用 Pillow 驗證文件內容
   - 如果文件內容不是有效的圖片格式，會拋出錯誤
   - HEIC 格式在轉換過程中可能出現問題

3. **驗證時機問題**:
   - 序列化器的 `validate_photo()` 已經處理了文件轉換
   - 但模型保存時，ImageField 會再次驗證
   - 如果轉換後的文件對象有問題，仍會失敗

## 當前實現的處理邏輯

### 1. 序列化器驗證 (`scoring/serializers.py`)

```python
def validate_photo(self, value):
    """驗證圖片文件"""
    if value is None:
        return value
    
    # 檢查文件大小
    if value.size > 10 * 1024 * 1024:
        raise serializers.ValidationError('圖片文件大小不能超過 10MB')
    
    # 獲取文件名和 content_type
    file_name = getattr(value, 'name', '') or ''
    content_type = getattr(value, 'content_type', None)
    
    # 檢查是否為 HEIC 格式
    is_heic = False
    if content_type:
        if 'heic' in content_type.lower() or 'heif' in content_type.lower():
            is_heic = True
    
    if not is_heic and file_name:
        if file_name.lower().endswith('.heic') or file_name.lower().endswith('.heif'):
            is_heic = True
    
    # HEIC 轉換流程
    if is_heic:
        try:
            import pyheif
            # 使用 pyheif 轉換為 JPEG
            heif_file = pyheif.read_heif(BytesIO(file_content))
            img = Image.frombytes(...)
            # 轉換為 RGB 並保存為 JPEG
            # 創建新的 InMemoryUploadedFile 對象
            return new_file
        except ImportError:
            # 嘗試使用 pillow-heif
        except Exception:
            # 後備方案：重命名文件
```

### 2. 前端處理 (`templates/leaderboard.html`)

```javascript
// 編輯路線表單提交
document.getElementById('editRouteForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    
    // 獲取照片文件
    const editRoutePhotoInput = document.getElementById('editRoutePhoto');
    const editRoutePhotoFromGallery = document.getElementById('editRoutePhotoFromGallery');
    let photoFile = null;
    if (editRoutePhotoInput && editRoutePhotoInput.files && editRoutePhotoInput.files[0]) {
        photoFile = editRoutePhotoInput.files[0];
    } else if (editRoutePhotoFromGallery && editRoutePhotoFromGallery.files && editRoutePhotoFromGallery.files[0]) {
        photoFile = editRoutePhotoFromGallery.files[0];
    }
    
    if (photoFile) {
        formData.append('photo', photoFile);
    }
    
    // 發送 PATCH 請求
    fetch(`/api/routes/${routeId}/`, {
        method: 'PATCH',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'include',
        body: formData
    })
});
```

## 問題診斷

### 可能的原因

1. **pyheif 轉換失敗但未正確處理**:
   - pyheif 可能無法正確讀取某些 iPhone 照片
   - 轉換後的 JPEG 文件可能有問題
   - 錯誤被吞掉，導致原始 HEIC 文件被傳遞到模型層

2. **文件名清理不完整**:
   - `route_photo_upload_path()` 函數可能無法處理所有特殊字符
   - 模型保存時 ImageField 驗證失敗

3. **文件對象狀態問題**:
   - 轉換後的文件對象可能沒有正確設置所有屬性
   - `InMemoryUploadedFile` 的某些屬性可能缺失

4. **Pillow 驗證時機**:
   - 即使序列化器已經驗證，模型保存時 ImageField 仍會驗證
   - 如果文件對象的某些屬性不正確，驗證會失敗

## 修復方案（已執行）

### ✅ 方案 1: 增強文件名清理（已實施）

在 `scoring/models.py` 的 `route_photo_upload_path()` 函數中，已加強文件名清理邏輯：

```python
def route_photo_upload_path(instance, filename):
    """
    生成路線照片的上傳路徑
    清理文件名，確保符合文件系統要求（特別是處理 iPhone 的文件名）
    """
    import os
    from django.utils.text import get_valid_filename
    from datetime import datetime
    
    # 獲取文件擴展名
    ext = os.path.splitext(filename)[1].lower()
    
    # 如果沒有擴展名，強制使用 .jpg
    if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        ext = '.jpg'
    
    # 生成安全的文件名（使用時間戳和路線ID）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    route_id = instance.id if instance.id else 'new'
    
    # 強制使用安全的文件名格式
    safe_filename = f'route_{route_id}_{timestamp}{ext}'
    
    return f'route_photos/{safe_filename}'
```

### ✅ 方案 2: 在序列化器中確保文件格式正確（已實施）

在 `validate_photo()` 方法中，已增強文件格式驗證和處理：

**已實施的修復**:

1. **使用 FileField 而不是 ImageField**（在 `RouteUpdateSerializer` 中）:
```python
photo = serializers.FileField(required=False, allow_null=True)
```
這樣可以繞過 Django 的自動 ImageField 驗證，允許手動驗證。

2. **增強 validate_photo() 方法**:
- 根據 Pillow 檢測到的實際圖片格式確定擴展名
- 如果文件沒有擴展名或擴展名不正確，創建新的文件對象
- 確保所有返回的文件對象都有正確的格式和擴展名
- 驗證文件可以被 Pillow 正確讀取

### 方案 3: 在模型層添加自定義驗證

在 `Route` 模型中重寫 `save()` 方法，在保存前確保照片格式正確：

```python
class Route(models.Model):
    # ... 現有字段 ...
    
    def save(self, *args, **kwargs):
        # 如果照片存在，確保格式正確
        if self.photo:
            try:
                from PIL import Image
                # 驗證圖片可以打開
                img = Image.open(self.photo)
                img.verify()
                # 重新打開以進行實際操作
                self.photo.seek(0)
                img = Image.open(self.photo)
                
                # 確保文件名有正確的擴展名
                if not self.photo.name or '.' not in self.photo.name:
                    # 根據圖片格式添加擴展名
                    format_ext = {
                        'JPEG': '.jpg',
                        'PNG': '.png',
                        'GIF': '.gif',
                        'BMP': '.bmp',
                        'WEBP': '.webp'
                    }
                    ext = format_ext.get(img.format, '.jpg')
                    # 更新文件名
                    base_name = os.path.splitext(self.photo.name)[0] if self.photo.name else 'photo'
                    self.photo.name = f'{base_name}{ext}'
            except Exception as e:
                # 如果驗證失敗，記錄錯誤但不阻止保存
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'照片驗證失敗: {str(e)}')
        
        super().save(*args, **kwargs)
```

## 已執行的修復步驟

✅ **已完成**:
1. **增強 `route_photo_upload_path()` 函數**: 強制使用安全的文件名格式（`route_{route_id}_{timestamp}.jpg`）
2. **優化 `validate_photo()` 方法**: 確保所有返回的文件對象都有正確的格式和擴展名
3. **修改 `RouteUpdateSerializer`**: 使用 `FileField` 而不是 `ImageField`，允許手動驗證
4. **創建測試用例**: 8 個測試用例全部通過，驗證修復有效

## 測試結果

**測試文件**: `scoring/tests/test_case_22_iphone_photo_update_route_fix.py`

**測試用例** (8 個，全部通過):
1. ✅ `test_iphone_camera_heic_update_route` - iPhone 拍照（HEIC 格式）更新路線
2. ✅ `test_iphone_camera_jpeg_update_route` - iPhone 拍照（JPEG 格式）更新路線
3. ✅ `test_iphone_gallery_photo_update_route` - iPhone 從圖庫選擇照片更新路線
4. ✅ `test_photo_without_extension_update_route` - 無擴展名文件更新路線
5. ✅ `test_photo_with_special_characters_update_route` - 特殊字符文件名更新路線
6. ✅ `test_photo_filename_format_validation` - 驗證文件名格式符合 ImageField 要求
7. ✅ `test_multiple_photo_updates_in_sequence` - 連續多次更新路線照片
8. ✅ `test_update_route_without_photo_change` - 更新路線但不改變照片

**測試結果**: 所有 8 個測試用例全部通過 ✅

## 測試建議

1. **測試場景**:
   - iPhone 拍照更新路線（第一次使用）
   - iPhone 從圖庫選擇照片更新路線
   - iPhone 拍照創建新路線
   - 不同 iPhone 型號和 iOS 版本

2. **驗證點**:
   - 照片能夠成功上傳
   - 照片文件名格式正確
   - 照片可以在前端正確顯示
   - 沒有 "The string did not match the expected pattern" 錯誤

## 相關文件

- `scoring/serializers.py`: `RouteUpdateSerializer.validate_photo()`
- `scoring/models.py`: `Route.photo` 字段和 `route_photo_upload_path()` 函數
- `templates/leaderboard.html`: 編輯路線表單提交邏輯

## 參考資料

- Django ImageField 文檔: https://docs.djangoproject.com/en/stable/ref/models/fields/#imagefield
- Pillow 文檔: https://pillow.readthedocs.io/
- pyheif 文檔: https://github.com/carsales/pyheif

