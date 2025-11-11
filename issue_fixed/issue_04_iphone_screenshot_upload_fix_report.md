# 工程報告：iPhone 屏幕截圖上傳失敗問題（已修復）

**狀態**: ✅ 已修復並驗證  
**修復日期**: 2025-11-11  
**測試結果**: 所有測試用例通過

## 問題描述

**症狀**: 在 iPhone 上使用屏幕截圖功能上傳圖片時，上傳會失敗。

**影響範圍**: 所有使用 iPhone 屏幕截圖功能上傳圖片的使用者。

**錯誤發生時機**: 
- 創建或更新路線時選擇屏幕截圖（通過截圖或從圖庫選擇）
- 特別是文件名包含中文字符（如"屏幕快照"）的情況

## 問題根源

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

## 修復方案

### ✅ 方案：增強文件名清理邏輯（已實施）

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

**修改位置**:

- `scoring/serializers.py` - `RouteCreateSerializer.validate_photo()` 方法
- `scoring/serializers.py` - `RouteUpdateSerializer.validate_photo()` 方法（通過調用 RouteCreateSerializer 的方法）

**關鍵代碼邏輯**:

```python
# 檢查是否包含非ASCII字符（包括中文）或特殊字符
has_non_ascii = any(ord(char) > 127 for char in base_name) if base_name else False
has_special_chars = bool(re.search(r'[^\w\-_\.]', base_name)) if base_name else False

# 如果文件名包含中文字符、特殊字符、過長或為空，使用安全的默認文件名
if not base_name or len(base_name) > 50 or has_non_ascii or has_special_chars:
    base_name = 'photo'
```

**處理場景**:

1. **文件名沒有擴展名**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
2. **擴展名不正確**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
3. **擴展名正確但文件名包含中文/特殊字符**: 檢測中文字符/特殊字符 → 使用 `photo.{detected_ext}`
4. **Pillow 驗證失敗但 content_type 有效**: 檢測中文字符/特殊字符 → 使用 `photo.{ext}`

## 測試結果

**測試文件**: `scoring/tests/test_case_iphone_screenshot_upload.py`

**測試用例** (3 個，全部通過):
1. ✅ `test_iphone_screenshot_chinese_filename` - iPhone 屏幕截圖（中文文件名：屏幕快照）
2. ✅ `test_iphone_screenshot_english_filename` - iPhone 屏幕截圖（英文文件名：Screenshot）
3. ✅ `test_iphone_screenshot_no_extension` - iPhone 屏幕截圖（沒有擴展名）

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

所有這些情況都會被自動轉換為安全的文件名格式（如 `photo.png`、`photo.jpg`），確保 ImageField 驗證通過。

## 相關文件

- `scoring/serializers.py`: `RouteCreateSerializer.validate_photo()` 和 `RouteUpdateSerializer.validate_photo()`
- `scoring/models.py`: `Route.photo` 字段和 `route_photo_upload_path()` 函數
- `scoring/tests/test_case_iphone_screenshot_upload.py`: iPhone 屏幕截圖上傳測試用例

## 參考資料

- Django ImageField 文檔: https://docs.djangoproject.com/en/stable/ref/models/fields/#imagefield
- Pillow 文檔: https://pillow.readthedocs.io/
- Python Unicode 處理: https://docs.python.org/3/howto/unicode.html

