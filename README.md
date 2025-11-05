# 攀岩計分系統

基於「分數逆向分配」邏輯的即時排行榜應用系統。

## 專案概述

本系統採用 Python/Django 作為後端框架，SQLite（預設）或 MySQL 作為資料庫，實現攀岩比賽的即時計分與排行榜功能。

### 核心計分公式

- **常態組**: 單線分數 $S_r = \frac{L}{P_r}$（$L$ 為每一條線總分，$P_r$ 為完成路線 $r$ 的常態組人數）
- **客製化組**: 每完成一條路線固定獲得 $L$ 分，不會被其他成員分攤分數

### 每一條線總分 (L) 自動計算

- **成員數 < 8 人**：使用 1 到成員數的最小公倍數 (LCM)
- **成員數 ≥ 8 人**：固定為 1000 分
- **無一般組成員**：預設為 1 分

## 技術棧

- **後端**: Python 3.8+ / Django 4.2
- **資料庫**: SQLite（預設）或 MySQL 5.7+（可選）
- **API**: Django REST Framework
- **前端**: HTML + CSS + JavaScript
- **圖片處理**: Pillow（支持手機照片上傳）

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
   - **首頁**: http://127.0.0.1:8000/（創建房間、查看房間列表）
   - **排行榜頁面**: http://127.0.0.1:8000/leaderboard/{room_id}/（管理成員、路線、查看排行榜）
   - **規則說明**: http://127.0.0.1:8000/rules/（查看計分規則說明）
   - **管理後台**: http://127.0.0.1:8000/admin/

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

### 創建房間

```
POST /api/rooms/
```

請求體格式：
```json
{
  "name": "房間名稱"
}
```

**注意**：`standard_line_score`（每一條線總分）會根據一般組成員數自動計算，無需手動設定。

### 新增成員

```
POST /api/members/
```

請求體格式：
```json
{
  "room": 1,
  "name": "成員名稱",
  "is_custom_calc": false
}
```

**注意**：成員名稱在同一房間內必須唯一。

### 新增路線

```
POST /api/rooms/{room_id}/routes/
```

請求體格式（JSON）：
```json
{
  "name": "路線1",
  "grade": "V4",
  "member_completions": {
    "1": true,
    "2": false,
    "3": true
  }
}
```

請求體格式（FormData，支持照片上傳）：
```
name: 路線1
grade: V4
photo: [文件]
member_completions: {"1":true,"2":false}
```

**注意**：
- 難度等級（grade）為必填項目，範圍：V1-V8+
- 路線名稱會自動加上【路線】前綴
- 支持照片上傳（手機可直接拍照）

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
- `standard_line_score`: 每一條線總分 (L)，根據一般組成員數自動計算
  - 成員數 < 8：LCM(1,2,...,N)
  - 成員數 ≥ 8：固定 1000
  - 無一般組成員：預設 1

### Member（成員）
- `room`: 外鍵關聯 Room
- `name`: 成員名稱（同一房間內必須唯一）
- `is_custom_calc`: 是否為客製化組
- `total_score`: 總分（自動計算）

### Route（路線）
- `room`: 外鍵關聯 Room
- `name`: 路線名稱（自動加上【路線】前綴）
- `grade`: 難度等級（V1-V8+，必填）
- `photo`: 照片文件（ImageField）
- `photo_url`: 照片網址（舊版，已棄用）

### Score（成績）
- `member`: 外鍵關聯 Member
- `route`: 外鍵關聯 Route
- `is_completed`: 是否完成
- `score_attained`: 獲得的分數（自動計算）

## 計分邏輯

核心計分邏輯實作於 `scoring/models.py` 中的 `update_scores(room_id)` 函式。

### 觸發時機

- 新增路線時
- 更新路線成員完成狀態時
- 更新成績狀態時
- 刪除路線時
- 新增/刪除/更新成員時
- 修改成員組別（常態組/客製化組）時

### 計算流程

1. 獲取房間的標準線數 $L$
2. 對於每條路線，計算完成該路線的常態組人數 $P_r$
3. 計算路線分數 $S_r = L / P_r$（若 $P_r > 0$）
4. 分配分數給完成該路線的常態組成員
5. 統計客製化組成員完成的路線數，計算總分（路線數 × $L$）
6. 更新所有成員的 `total_score`

## 測試

### 運行測試

```bash
python manage.py test scoring.tests
```

### 測試案例

系統包含以下測試案例：

1. **核心計分邏輯測試**（`ScoringLogicTestCase`）：
   - 循序漸進新增路線的計分
   - 標記完成/未完成狀態的計分更新
   - 刪除路線後的計分重算
   - 客製化組與常態組的分數獨立計算

2. **API 接口測試**（`APITestCase`）：
   - 獲取排行榜
   - 創建路線
   - 更新成績狀態

### GitHub Actions 測試

項目已配置 GitHub Actions 自動測試，每次推送代碼時會自動運行測試。詳見 `.github/workflows/test.yml`。

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

