# Excel 圖片嵌入儲存格功能說明

## 概述

此功能使用 **Spire.XLS for Python** 實現將圖片精準嵌入 Excel 儲存格的功能，圖片尺寸和位置與儲存格嚴密對齊，達到「圖片嵌入儲存格」的效果。

## 安裝依賴

首先需要安裝 Spire.XLS for Python：

```bash
pip install Spire.XLS
```

或者安裝項目的所有依賴：

```bash
pip install -r requirements.txt
```

## 核心功能

### 主要特性

- ✅ 在指定儲存格插入圖片
- ✅ 自動調整圖片尺寸匹配儲存格
- ✅ 調整儲存格列寬與行高
- ✅ 設置圖片與儲存格邊界的偏移距離
- ✅ 保持圖片寬高比
- ✅ 支援多種圖片格式（PNG, JPEG, BMP, GIF 等）
- ✅ 批量插入多張圖片
- ✅ 創建圖片網格佈局

## 使用方法

### 方法 1: 使用 ExcelImageEmbedder 類

```python
from scoring.utils_excel_image import ExcelImageEmbedder

# 創建工具實例
embedder = ExcelImageEmbedder()

# 在 A1 儲存格插入圖片
picture = embedder.insert_image_to_cell(
    image_path='path/to/image.jpg',
    row_index=1,          # 第 1 行
    column_index=1,       # 第 1 列（A 列）
    offset_x=2,           # 左邊距 2 像素
    offset_y=2,           # 上邊距 2 像素
    auto_resize_cell=True,      # 自動調整儲存格大小
    preserve_aspect_ratio=True  # 保持圖片寬高比
)

# 保存 Excel 文件
embedder.save('output.xlsx')
```

### 方法 2: 使用便捷函數

```python
from scoring.utils_excel_image import create_excel_with_embedded_images

# 準備圖片數據列表
image_data_list = [
    {
        'image_path': 'photo1.jpg',
        'row': 1,
        'column': 1,
        'offset_x': 2,
        'offset_y': 2,
        'auto_resize': True
    },
    {
        'image_path': 'photo2.png',
        'row': 1,
        'column': 2,
        'offset_x': 5,
        'offset_y': 5,
        'auto_resize': True
    }
]

# 創建包含嵌入圖片的 Excel 文件
create_excel_with_embedded_images(
    output_path='output.xlsx',
    image_data_list=image_data_list,
    sheet_name='圖片工作表'
)
```

## API 參考

### ExcelImageEmbedder 類

#### 初始化

```python
embedder = ExcelImageEmbedder(workbook_path=None)
```

- `workbook_path`: 可選，現有 Excel 文件路徑。如果為 None，則創建新工作簿

#### insert_image_to_cell()

在指定儲存格插入圖片並精準對齊。

**參數：**
- `image_path` (str): 圖片文件路徑
- `row_index` (int): 行索引（從 1 開始）
- `column_index` (int): 列索引（從 1 開始）
- `offset_x` (int): 圖片與儲存格左邊界的水平偏移（像素，默認 0）
- `offset_y` (int): 圖片與儲存格上邊界的垂直偏移（像素，默認 0）
- `auto_resize_cell` (bool): 是否自動調整儲存格大小（默認 True）
- `preserve_aspect_ratio` (bool): 是否保持圖片寬高比（默認 True）

**返回：**
- `ExcelPicture`: 插入的圖片對象

#### set_cell_size()

手動設置儲存格的列寬和行高。

**參數：**
- `row_index` (int): 行索引
- `column_index` (int): 列索引
- `width_points` (float): 列寬（單位：點，1 點 = 1/72 英寸）
- `height_points` (float): 行高（單位：點）

#### get_worksheet()

獲取工作表對象。

**參數：**
- `sheet_name` (str): 工作表名稱（優先使用）
- `sheet_index` (int): 工作表索引（如果未提供名稱）

#### save()

保存 Excel 文件。

**參數：**
- `output_path` (str): 輸出文件路徑（.xlsx 格式）

#### save_to_bytes()

將工作簿保存為字節流（用於 Web 應用）。

**返回：**
- `bytes`: Excel 文件的字節數據

## 使用範例

詳細的使用範例請參考 `excel_image_embedding_example.py` 文件，其中包含：

1. **基本使用** - 單張圖片嵌入
2. **多張圖片** - 批量插入圖片
3. **自定義大小** - 手動設置儲存格大小
4. **網格佈局** - 創建圖片網格
5. **圖片與文字** - 在圖片旁邊添加說明文字

運行範例：

```bash
python scoring/excel_image_embedding_example.py
```

## 注意事項

### 單位說明

- **行高和列寬**：使用「點」（points）作為單位，1 點 = 1/72 英寸
- **圖片偏移**：使用「像素」（pixels）作為單位
- **轉換關係**：1 點 ≈ 1.33 像素（假設 96 DPI）

### 圖片格式支援

支援常見的圖片格式：
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- GIF (.gif)
- 其他 Spire.XLS 支援的格式

### 性能考慮

- 插入大量圖片時，建議分批處理
- 大尺寸圖片會增加文件大小，可考慮預先壓縮
- 使用 `auto_resize_cell=False` 可以避免頻繁調整儲存格大小

### 與現有 openpyxl 功能的區別

項目中已有使用 `openpyxl` 的 Excel 導出功能。Spire.XLS 的優勢在於：

- 更精確的圖片對齊控制
- 更好的圖片嵌入儲存格效果
- 支援更複雜的圖片佈局

兩者可以根據需求選擇使用。

## 整合到 Django 視圖

如果需要將此功能整合到 Django 視圖中，可以這樣使用：

```python
from scoring.utils_excel_image import ExcelImageEmbedder
from django.http import HttpResponse

def export_excel_with_images(request):
    embedder = ExcelImageEmbedder()
    
    # 插入圖片
    embedder.insert_image_to_cell(
        image_path='media/route_photos/route_1.jpg',
        row_index=1,
        column_index=1
    )
    
    # 保存為字節流
    excel_bytes = embedder.save_to_bytes()
    
    # 返回 HTTP 響應
    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="export.xlsx"'
    return response
```

## 故障排除

### 問題：ImportError: No module named 'spire'

**解決方案：**
```bash
pip install Spire.XLS
```

### 問題：圖片無法顯示或位置不正確

**可能原因：**
- 圖片路徑不正確
- 儲存格大小設置不當
- 偏移量設置過大

**解決方案：**
- 確認圖片文件存在
- 使用 `auto_resize_cell=True` 自動調整
- 減少偏移量值

### 問題：Excel 文件無法打開

**可能原因：**
- 文件損壞
- 版本不兼容

**解決方案：**
- 確保使用正確的保存方法
- 檢查 Spire.XLS 版本是否支援 Excel 2016+ 格式

## 相關文件

- `scoring/utils_excel_image.py` - 核心工具類
- `scoring/excel_image_embedding_example.py` - 使用範例
- `requirements.txt` - 項目依賴列表

## 授權說明

Spire.XLS for Python 是商業軟件，有免費版本和付費版本。請根據需求選擇合適的版本。

免費版本限制：
- 每個文件最多 5 個工作表
- 每個工作表最多 200 行
- 文件會包含水印

付費版本無以上限制。

## 更新日誌

- **2025-01-XX**: 初始版本，實現基本的圖片嵌入儲存格功能

