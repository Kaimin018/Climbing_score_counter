# 攀岩計分系統

基於「分數逆向分配」邏輯的即時排行榜應用系統。

## 專案概述

本系統採用 Python/Django 作為後端框架，MySQL 作為資料庫，實現攀岩比賽的即時計分與排行榜功能。

### 核心計分公式

- **常態組**: 單線分數 $S_r = \frac{L}{P_r}$（$L$ 為標準線數，$P_r$ 為完成路線 $r$ 的常態組人數）
- **客製化組**: 每完成一條路線得分 $L$ 分

## 技術棧

- **後端**: Python 3.x / Django 4.2
- **資料庫**: MySQL
- **API**: Django REST Framework
- **前端**: HTML + CSS + JavaScript

## 快速開始

### 一鍵啟動（推薦）

1. **安裝依賴**：
   ```bash
   pip install -r requirements.txt
   ```

2. **運行啟動腳本**：
   
   **Windows PowerShell**：
   ```powershell
   .\start_server.ps1
   ```
   
   **Windows CMD**：
   ```cmd
   start_server.bat
   ```
   
   **Linux/macOS**：
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

   啟動腳本會自動完成：
   - ✅ 數據庫遷移
   - ✅ 初始化默認數據（房間和成員）
   - ✅ 啟動服務器

3. **訪問系統**：
   - 排行榜頁面：http://127.0.0.1:8000/api/leaderboard/1/
   - 管理後台：http://127.0.0.1:8000/admin/

## 詳細設置

### 環境要求

- Python 3.8+
- SQLite（預設，無需安裝）或 MySQL 5.7+（可選）
- pip

### 手動設置步驟

如果需要手動設置，請參考 `SETUP.md` 文件獲取詳細說明。

主要包括：
1. 安裝依賴
2. 配置數據庫（預設使用 SQLite）
3. 運行遷移
4. 初始化數據（`python manage.py init_default_data`）
5. 啟動服務器

## API 接口

### 獲取排行榜

```
GET /api/rooms/{room_id}/leaderboard/
```

返回格式：
```json
{
  "room_info": {
    "name": "房間名稱",
    "standard_line_score": 12,
    "id": 1
  },
  "leaderboard": [
    {
      "id": 1,
      "name": "成員名稱",
      "is_custom_calc": false,
      "total_score": "48.00",
      "completed_routes_count": 5
    }
  ]
}
```

### 新增路線

```
POST /api/rooms/{room_id}/routes/
```

請求體格式：
```json
{
  "name": "路線名稱",
  "grade": "V4",
  "photo_url": "https://example.com/photo.jpg",
  "member_completions": {
    "1": true,
    "2": false,
    "3": true
  }
}
```

### 更新成績狀態

```
PATCH /api/scores/{score_id}/
```

請求體格式：
```json
{
  "is_completed": true
}
```

### 刪除路線

```
DELETE /api/routes/{route_id}/
```

刪除路線後會自動觸發計分更新。

## 資料庫結構

### Room（房間）
- `name`: 房間名稱
- `standard_line_score`: 標準線數 (L)，預設 12

### Member（成員）
- `room`: 外鍵關聯 Room
- `name`: 成員名稱
- `is_custom_calc`: 是否為客製化組
- `total_score`: 總分

### Route（路線）
- `room`: 外鍵關聯 Room
- `name`: 路線名稱
- `grade`: 難度等級
- `photo_url`: 照片網址

### Score（成績）
- `member`: 外鍵關聯 Member
- `route`: 外鍵關聯 Route
- `is_completed`: 是否完成
- `score_attained`: 獲得的分數

## 計分邏輯

核心計分邏輯實作於 `scoring/models.py` 中的 `update_scores(room_id)` 函式。

### 觸發時機

- 新增路線時
- 更新成績狀態時
- 刪除路線時

### 計算流程

1. 獲取房間的標準線數 $L$
2. 對於每條路線，計算完成該路線的常態組人數 $P_r$
3. 計算路線分數 $S_r = L / P_r$（若 $P_r > 0$）
4. 分配分數給完成該路線的常態組成員
5. 統計客製化組成員完成的路線數，計算總分（路線數 × $L$）
6. 更新所有成員的 `total_score`

## 測試案例

參考文檔中的測試案例，系統已實現以下功能：

1. 循序漸進新增路線的計分
2. 標記完成/未完成狀態的計分更新
3. 刪除路線後的計分重算
4. 客製化組與常態組的分數獨立計算

## 開發與維護

### 管理後台

訪問 `/admin/` 可以使用 Django 管理後台管理所有數據。

### 添加測試數據

可以使用 Django shell 或管理後台添加測試數據：

```python
python manage.py shell
```

```python
from scoring.models import Room, Member

# 創建房間
room = Room.objects.create(name="測試房間", standard_line_score=12)

# 創建成員
Member.objects.create(room=room, name="王小明", is_custom_calc=False)
Member.objects.create(room=room, name="李大華", is_custom_calc=False)
Member.objects.create(room=room, name="張三", is_custom_calc=True)
```

## 許可證

本專案僅供學習與開發使用。

