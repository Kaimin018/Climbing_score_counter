# 工程報告：iPhone 屏幕截圖上傳問題完整修復

**狀態**: ✅ 已修復並驗證  
**修復日期**: 2025-11-11  
**測試結果**: 所有測試用例通過

## 問題描述

**症狀**: 在 iPhone 上使用屏幕截圖功能上傳圖片時，上傳會失敗，出現多種錯誤。

**影響範圍**: 
- 所有使用 iPhone 屏幕截圖功能上傳圖片的使用者
- 特別是在移動設備上傳圖片時
- 使用文件名如 `IMG_0937.PNG` 或包含中文字符的 iPhone 截圖

**錯誤發生時機**: 
- 創建或更新路線時選擇屏幕截圖（通過截圖或從圖庫選擇）
- 特別是文件名包含中文字符（如"屏幕快照"）的情況
- 當文件對象是 `BufferedRandom` 或 `BufferedReader` 類型時

**錯誤訊息**:
1. `TypeError: cannot pickle 'BufferedRandom' instances` - 文件對象序列化錯誤
2. ImageField 驗證失敗 - 文件名包含中文字符或特殊字符

## 問題根源

這個問題包含兩個相關但不同的方面：

### 問題 1: 文件名驗證失敗

**核心問題**: 當 iPhone 屏幕截圖的文件名包含中文字符或特殊字符時，即使序列化器已經處理了文件，Django 的 `ImageField` 在模型保存時仍會驗證文件名。如果文件名包含非 ASCII 字符（如中文）或特殊字符，可能會導致驗證失敗。

**具體原因**:

1. **文件名包含中文字符**:
   - iPhone 屏幕截圖通常保存為 PNG 格式
   - 文件名可能包含中文字符（如"屏幕快照 2025-01-01 12.00.00.png"）
   - 即使擴展名正確，文件名中的中文字符可能導致 ImageField 驗證失敗

2. **文件名包含特殊字符**:
   - 文件名可能包含空格、標點符號等特殊字符
   - 這些字符可能不符合文件系統或 ImageField 的驗證要求

3. **驗證時機問題**:
   - 序列化器的 `validate_photo()` 已經處理了文件轉換
   - 但模型保存時，ImageField 仍會驗證文件名
   - 如果文件名包含中文字符或特殊字符，驗證可能失敗

### 問題 2: BufferedRandom 對象 Pickle 錯誤

**核心問題**: Django 在處理文件上傳時，如果文件對象是 `BufferedRandom` 或 `BufferedReader` 類型，這些對象無法被 pickle（序列化），導致在以下情況出現錯誤：

1. **`request.data.copy()` 深拷貝時**:
   - Django 的 `request.data.copy()` 會嘗試深拷貝所有數據
   - 深拷貝會觸發 pickle 序列化
   - `BufferedRandom` 對象無法被 pickle，導致錯誤

2. **模型保存時**:
   - Django 在保存模型時，會嘗試序列化文件對象
   - 如果文件對象是 `BufferedRandom`，會導致 pickle 錯誤

3. **文件對象類型問題**:
   - 在 Windows 上，使用 `'rb'` 模式打開文件返回 `BufferedReader`
   - 使用 `'r+b'` 模式打開文件返回 `BufferedRandom`
   - 這兩種類型都無法被 pickle

**具體原因**:

1. **文件對象類型**:
   - `BufferedRandom` 和 `BufferedReader` 是 Python 的內建文件對象類型
   - 這些對象包含文件系統狀態，無法被序列化
   - Django 需要可序列化的文件對象（如 `InMemoryUploadedFile`）

2. **錯誤發生位置**:
   - 主要在 `scoring/views.py` 的 `RouteViewSet.update()` 方法中
   - 當執行 `data = request.data.copy()` 時觸發
   - 也在 `scoring/serializers.py` 的保存操作時觸發

3. **移動設備特殊性**:
   - iPhone 截圖文件名如 `IMG_0937.PNG`
   - 移動設備上傳時，文件對象可能是 `BufferedRandom` 類型
   - 需要特別處理這些文件對象

## 修復方案

### ✅ 方案 1: 增強文件名清理邏輯（已實施）

在 `scoring/serializers.py` 的 `validate_photo()` 方法中，增強了對包含中文字符或特殊字符的文件名的處理：

**修復內容**:

1. **檢測非 ASCII 字符**:
   - 檢查文件名是否包含非 ASCII 字符（包括中文）
   - 使用 `any(ord(char) > 127 for char in base_name)` 檢測

2. **檢測特殊字符**:
   - 使用正則表達式檢測文件名中的特殊字符
   - 只允許字母、數字、連字符、下劃線和點號

3. **使用安全文件名**:
   - 如果檢測到中文字符或特殊字符，使用安全的默認文件名（`photo.png`、`photo.jpg` 等）
   - 確保文件名符合 ImageField 的驗證要求

**關鍵代碼邏輯**:

```python
# 檢查是否包含非ASCII字符（包括中文）或特殊字符
has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False

# 如果文件名包含中文字符、特殊字符、過長或為空，使用安全的默認文件名
if not base_name or len(base_name) > 50 or has_non_ascii or has_special_chars:
    base_name = 'photo'
```

### ✅ 方案 2: 統一文件對象轉換函數（已實施）

創建了一個統一的文件對象轉換函數 `convert_file_to_uploaded_file()`，並在關鍵位置使用它：

**修復內容**:

1. **創建轉換函數** (`scoring/serializers.py`):
   ```python
   def convert_file_to_uploaded_file(file_obj):
       """
       強制將文件對象轉換為 InMemoryUploadedFile，避免 pickle 錯誤
       
       處理所有可能的文件對象類型：
       - BufferedRandom
       - BufferedReader
       - 包裝在 UploadedFile 中的 BufferedRandom/BufferedReader
       - 其他不可序列化的文件對象
       """
   ```
   - 檢測文件對象類型
   - 如果是 `BufferedRandom` 或 `BufferedReader`，讀取內容並創建 `InMemoryUploadedFile`
   - 檢查內部 `file` 屬性（包裝在 `UploadedFile` 中的情況）
   - 確保所有不可序列化的文件對象都被轉換

2. **視圖層修復** (`scoring/views.py`):
   - 在 `RouteViewSet.update()` 方法中，不再使用 `request.data.copy()`
   - 手動遍歷 `request.data`，在複製前先轉換文件對象
   - 對於 `photo` 字段，使用 `convert_file_to_uploaded_file()` 轉換
   - 正確處理 `QueryDict` 的列表值

3. **序列化器層修復** (`scoring/serializers.py`):
   - 在 `RouteCreateSerializer.create()` 中使用轉換函數
   - 在 `RouteUpdateSerializer.update()` 中使用轉換函數
   - 在保存前檢查文件對象類型，確保是可序列化的

4. **增強日誌記錄**:
   - 添加詳細的日誌記錄，追蹤文件對象轉換過程
   - 記錄文件對象的原始類型和轉換後的類型
   - 記錄完整的錯誤堆棧（如果轉換失敗）

## 修復細節

### 1. 文件名清理邏輯

**處理場景**:

1. **文件名沒有擴展名**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
2. **擴展名不正確**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
3. **擴展名正確但文件名包含中文/特殊字符**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
4. **Pillow 驗證失敗但 content_type 有效**: 檢測中文字符/特殊字符 → 使用 `photo.{ext}`

### 2. 文件對象轉換邏輯

**轉換流程**:
1. 檢查是否已經是 `InMemoryUploadedFile` 或 `SimpleUploadedFile`
   - 如果是，檢查內部 `file` 屬性是否為 `BufferedRandom`
   - 如果是，讀取內容並創建新的 `InMemoryUploadedFile`
2. 檢查是否直接是 `BufferedRandom` 或 `BufferedReader`
   - 如果是，讀取內容並創建 `InMemoryUploadedFile`
3. 檢查是否包裝在 `UploadedFile` 中
   - 檢查 `file` 屬性是否為 `BufferedRandom` 或 `BufferedReader`
   - 如果是，讀取內容並創建 `InMemoryUploadedFile`
4. 如果都不匹配，嘗試讀取內容並創建新文件（安全起見）

### 3. 視圖層修復

**修復前**:
```python
data = request.data.copy()  # 這裡會觸發 pickle 錯誤
```

**修復後**:
```python
data = {}
for key in request.data.keys():
    values = request.data.getlist(key)
    if key == 'photo' and values:
        photo_value = values[0] if values else None
        if photo_value:
            converted_photo = convert_file_to_uploaded_file(photo_value)
            data[key] = converted_photo
    else:
        # 處理其他字段
        if len(values) == 1:
            data[key] = values[0]
        else:
            data[key] = values
```

### 4. 序列化器層修復

**修復前**:
```python
if is_buffered_random:
    # 手動轉換邏輯...
    route.photo = new_file
else:
    route.photo = photo_data
```

**修復後**:
```python
converted_photo = convert_file_to_uploaded_file(photo_data)
route.photo = converted_photo
```

## 測試驗證

### 測試用例

1. **iPhone 截圖上傳測試** (`scoring/tests/test_case_iphone_screenshot_upload.py`):
   - ✅ `test_iphone_screenshot_chinese_filename` - iPhone 屏幕截圖（中文文件名：屏幕快照）
   - ✅ `test_iphone_screenshot_english_filename` - iPhone 屏幕截圖（英文文件名：Screenshot）
   - ✅ `test_iphone_screenshot_no_extension` - iPhone 屏幕截圖（沒有擴展名）

2. **BufferedRandom Pickle 錯誤修復測試** (`scoring/tests/test_case_32_buffered_random_pickle_fix.py`):
   - ✅ `test_create_route_with_buffered_random_file` - 使用 `BufferedRandom` 文件對象創建路線
   - ✅ `test_update_route_with_buffered_random_file` - 使用 `BufferedRandom` 文件對象更新路線
   - ✅ `test_create_route_with_buffered_reader_file` - 使用 `BufferedReader` 文件對象創建路線
   - ✅ `test_update_route_replace_photo_with_buffered_random` - 使用 `BufferedRandom` 文件對象替換現有照片
   - ✅ `test_update_route_with_iphone_screenshot_filename` - 使用 iPhone 截圖文件名（`IMG_0937.PNG`）更新路線
   - ✅ `test_create_route_with_iphone_screenshot_filename` - 使用 iPhone 截圖文件名創建路線

**回歸測試**:
- ✅ `test_case_16_iphone_photo_upload.TestCaseIPhonePhotoUpload.test_iphone_filename_with_unicode` - Unicode 文件名測試通過
- ✅ `test_case_07_route_photo_upload` - 所有 6 個測試用例通過

**測試結果**: 所有測試用例全部通過 ✅

## 修復效果

修復後，系統能夠正確處理：

1. ✅ **中文文件名**: 如"屏幕快照 2025-01-01 12.00.00.png"
2. ✅ **英文文件名**: 如"Screenshot 2025-01-01 at 12.00.00 PM.png"
3. ✅ **無擴展名文件**: 如"屏幕快照 2025-01-01 12.00.00"
4. ✅ **特殊字符文件名**: 如包含空格、標點符號的文件名
5. ✅ **Unicode 字符文件名**: 如"照片_2025年1月1日.jpg"
6. ✅ **BufferedRandom 文件對象**: 自動轉換為可序列化的類型
7. ✅ **BufferedReader 文件對象**: 自動轉換為可序列化的類型
8. ✅ **iPhone 截圖文件名**: 如 `IMG_0937.PNG`

所有這些情況都會被自動處理：
- 文件名會被清理為安全格式（如 `photo.png`、`photo.jpg`）
- 文件對象會被轉換為 `InMemoryUploadedFile`
- 確保 ImageField 驗證通過
- 確保不會出現 pickle 錯誤

## 相關文件

### 修改的文件

1. **`scoring/serializers.py`**:
   - 添加 `convert_file_to_uploaded_file()` 函數
   - 修改 `RouteCreateSerializer.validate_photo()` 方法（文件名清理）
   - 修改 `RouteCreateSerializer.create()` 方法（文件對象轉換）
   - 修改 `RouteUpdateSerializer.validate_photo()` 方法（文件名清理）
   - 修改 `RouteUpdateSerializer.update()` 方法（文件對象轉換）
   - 增強錯誤處理和日誌記錄

2. **`scoring/views.py`**:
   - 修改 `RouteViewSet.update()` 方法
   - 在複製 `request.data` 前先轉換文件對象
   - 正確處理 `QueryDict` 的列表值

3. **`scoring/models.py`**:
   - `Route.photo` 字段和 `route_photo_upload_path()` 函數

4. **`climbing_system/settings.py`**:
   - 增強日誌配置，支持完整的堆棧跟踪
   - 添加詳細的日誌格式化器

### 新增的文件

1. **`scoring/tests/test_case_iphone_screenshot_upload.py`**:
   - iPhone 屏幕截圖上傳測試用例

2. **`scoring/tests/test_case_32_buffered_random_pickle_fix.py`**:
   - BufferedRandom pickle 錯誤修復測試用例

3. **`scoring/utils.py`**:
   - 添加日誌相關的工具函數
   - 支持移動設備的日誌文件存儲

## 日誌改進

為了更好地追蹤和調試問題，增強了日誌系統：

1. **詳細的日誌格式**:
   - 包含文件路徑、行號、函數名
   - 包含進程 ID 和線程 ID

2. **完整的錯誤堆棧**:
   - 使用 `traceback.format_exception()` 記錄完整堆棧
   - 遍歷所有堆棧幀（最多 50 個）
   - 記錄局部變量信息

3. **Pickle 錯誤檢測**:
   - 自動檢測 pickle 相關錯誤
   - 記錄文件對象類型信息
   - 提供明確的錯誤提示

## 移動設備支持

修復還包括對移動設備的支持：

1. **日誌文件存儲**:
   - 支持 Android 和 iOS 設備
   - 自動檢測平台並選擇合適的存儲位置
   - 支持日誌輪轉（最大 10MB，保留 5 個備份）

2. **API 端點**:
   - 新增 `/api/routes/log-info/` 端點
   - 可以查看日誌文件位置和平台信息

## 修復效果對比

### 修復前

- ❌ iPhone 截圖上傳失敗（文件名包含中文字符）
- ❌ 更新路線時上傳圖片會出現 `TypeError: cannot pickle 'BufferedRandom' instances` 錯誤
- ❌ 錯誤發生在 `request.data.copy()` 時
- ❌ 無法處理 `BufferedRandom` 類型的文件對象
- ❌ 文件名包含特殊字符時驗證失敗

### 修復後

- ✅ 所有文件對象類型都被正確轉換為 `InMemoryUploadedFile`
- ✅ 不再出現 pickle 錯誤
- ✅ 支持 `BufferedRandom` 和 `BufferedReader` 類型
- ✅ 支持包裝在 `UploadedFile` 中的文件對象
- ✅ 文件名自動清理為安全格式
- ✅ 支持中文、特殊字符、Unicode 字符的文件名
- ✅ 完整的日誌記錄，便於調試
- ✅ 移動設備支持

## 注意事項

1. **性能影響**:
   - 文件對象轉換會讀取文件內容到內存
   - 對於大文件，可能會增加內存使用
   - 但這是必要的，因為 `BufferedRandom` 無法被序列化

2. **兼容性**:
   - 修復向後兼容，不影響現有功能
   - 對於已經是 `InMemoryUploadedFile` 的文件對象，會檢查內部文件對象
   - 對於正常的文件名，不會進行不必要的轉換

3. **錯誤處理**:
   - 如果轉換失敗，會記錄詳細的錯誤信息
   - 仍然嘗試使用原文件對象（可能會導致錯誤，但至少記錄了錯誤）

## 總結

這次修復完整解決了 iPhone 屏幕截圖上傳的問題，包括兩個方面：

1. **文件名驗證問題**: 通過增強文件名清理邏輯，自動處理包含中文字符、特殊字符或 Unicode 字符的文件名，確保符合 ImageField 的驗證要求。

2. **文件對象序列化問題**: 通過創建統一的文件對象轉換函數，在視圖層和序列化器層都進行了轉換，確保所有不可序列化的文件對象（如 `BufferedRandom`、`BufferedReader`）都被轉換為可序列化的 `InMemoryUploadedFile`。

修復還包括增強日誌記錄和移動設備支持，提高了系統的穩定性和可調試性。現在系統可以正確處理各種 iPhone 截圖上傳場景，無論是文件名格式還是文件對象類型。

## 參考資料

- Django ImageField 文檔: https://docs.djangoproject.com/en/stable/ref/models/fields/#imagefield
- Pillow 文檔: https://pillow.readthedocs.io/
- Python Unicode 處理: https://docs.python.org/3/howto/unicode.html
- Python Pickle 文檔: https://docs.python.org/3/library/pickle.html
