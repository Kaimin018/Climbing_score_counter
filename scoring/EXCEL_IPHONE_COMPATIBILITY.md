# Excel 圖片在 iPhone 上顯示問題 - 解決方案

## 問題描述

在 iPhone 上打開 Excel 文件時，圖片無法顯示。這是一個常見的兼容性問題。

## 根本原因

1. **圖片格式不兼容**
   - 某些圖片格式（如 HEIC、WebP）在 iPhone 的 Excel 應用中可能不支持
   - 解決方案：統一轉換為標準 JPEG 格式

2. **圖片嵌入方式問題**
   - 如果圖片是通過鏈接插入的（而非嵌入），在其他設備上可能無法顯示
   - 解決方案：確保圖片直接嵌入到 Excel 文件中

3. **Excel 文件格式問題**
   - 某些 Excel 格式可能不兼容
   - 解決方案：使用標準的 .xlsx 格式

## 已實施的解決方案

### 1. 圖片格式標準化

在 `scoring/views.py` 的 `export_excel` 方法中：

```python
# 調整照片大小並保存為標準 JPEG 格式
img = PILImage.open(photo_path)
img = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
img.save(temp_path, 'JPEG', quality=85)
```

**關鍵點：**
- 所有圖片統一轉換為 JPEG 格式
- 使用高質量設置（quality=85）確保圖片清晰
- 限制圖片大小以適應儲存格

### 2. 使用 openpyxl 正確嵌入圖片

```python
# 使用 openpyxl 的標準方法插入圖片
excel_img = ExcelImage(temp_path)
routes_ws.add_image(excel_img, cell_coord)
```

**關鍵點：**
- `add_image` 方法會自動將圖片嵌入到 Excel 文件中
- 圖片不是鏈接，而是直接嵌入，確保在所有設備上都能顯示
- 使用儲存格座標（如 'D5'）來定位圖片

### 3. 圖片大小優化

```python
# 限制圖片最大尺寸，確保在 iPhone 上能正常顯示
max_excel_width = 200  # Excel 單位
max_excel_height = 150  # Excel 單位

# 按比例縮小過大的圖片
if excel_img.width > max_excel_width or excel_img.height > max_excel_height:
    scale_ratio = min(width_ratio, height_ratio)
    excel_img.width = excel_img.width * scale_ratio
    excel_img.height = excel_img.height * scale_ratio
```

**關鍵點：**
- 限制圖片大小，避免文件過大
- 保持圖片寬高比
- 確保圖片能適應儲存格大小

## 為什麼不使用 Spire.XLS？

雖然 Spire.XLS 功能強大，但對於這個特定問題：

1. **openpyxl 已經足夠**
   - openpyxl 是 Python 中最流行的 Excel 操作庫
   - 完全開源，無需授權
   - 生成的 Excel 文件兼容性更好

2. **更好的兼容性**
   - openpyxl 生成的 .xlsx 文件在各種設備上兼容性更好
   - 特別是移動設備（如 iPhone）

3. **更簡單的實現**
   - 不需要處理複雜的 Placement 屬性
   - 標準的 `add_image` 方法就能正確嵌入圖片

## 驗證方法

1. **在電腦上驗證**
   - 用 Excel 或 LibreOffice 打開生成的文件
   - 確認圖片正常顯示

2. **在 iPhone 上驗證**
   - 將文件傳送到 iPhone
   - 使用 Microsoft Excel 應用打開
   - 確認圖片正常顯示

3. **檢查文件大小**
   - 如果圖片正確嵌入，文件大小應該明顯增加
   - 如果文件大小很小，可能圖片沒有正確嵌入

## 常見問題

### Q: 圖片仍然不顯示怎麼辦？

A: 檢查以下幾點：
1. 確認圖片文件路徑正確
2. 確認圖片格式是 JPEG
3. 確認使用 openpyxl 的 `add_image` 方法（不是其他方法）
4. 嘗試在電腦上打開文件，確認圖片是否嵌入

### Q: 圖片顯示但位置不對？

A: 調整以下參數：
1. 儲存格座標（cell_coord）
2. 圖片大小（excel_img.width 和 excel_img.height）
3. 行高和列寬

### Q: 文件太大怎麼辦？

A: 可以：
1. 降低圖片質量（quality 參數）
2. 進一步縮小圖片尺寸
3. 使用圖片壓縮

## 技術細節

### 單位轉換

- **像素 (pixels)**: 圖片的基本單位
- **點 (points)**: Excel 行高的單位，1 點 = 1/72 英寸
- **字符寬度**: Excel 列寬的單位

轉換關係：
- 1 點 ≈ 1.33 像素（假設 96 DPI）
- 1 像素 ≈ 0.75 點
- 列寬（字符）≈ (像素寬度 / 7) + 2

### openpyxl 圖片嵌入機制

openpyxl 的 `add_image` 方法會：
1. 讀取圖片文件
2. 將圖片數據嵌入到 Excel 文件的內部結構中
3. 創建圖片對象並設置位置
4. 圖片成為 Excel 文件的一部分，不依賴外部文件

這確保了圖片在所有設備上都能正常顯示。

