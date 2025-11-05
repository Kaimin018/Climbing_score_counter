# 專案架構文檔

## 專案概述

攀岩計分系統是一個基於 Django 的 Web 應用，實現攀岩比賽的即時計分與排行榜功能。系統採用前後端分離的架構，使用 Django REST Framework 提供 API 服務。

## 整體架構

```
climbing_score_counting_system/
├── climbing_system/          # Django 專案主配置
│   ├── settings.py          # 專案設定
│   ├── urls.py             # 主 URL 路由
│   ├── wsgi.py             # WSGI 配置
│   └── asgi.py             # ASGI 配置
├── scoring/                 # 核心應用模組
│   ├── models.py           # 資料模型
│   ├── views.py            # 視圖邏輯（API + 頁面）
│   ├── serializers.py      # API 序列化器
│   ├── urls.py             # API 路由
│   ├── admin.py            # Django Admin 配置
│   ├── management/         # 管理命令
│   │   └── commands/
│   │       └── init_default_data.py
│   ├── migrations/         # 資料庫遷移文件
│   └── tests/              # 測試模組
│       ├── test_api.py
│       └── test_case_01_default_member.py
├── templates/              # HTML 模板
│   ├── base.html
│   ├── index.html          # 首頁（房間列表）
│   ├── leaderboard.html    # 排行榜頁面
│   └── rules.html          # 規則說明頁面
├── static/                 # 靜態文件
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── .github/                # GitHub Actions
│   └── workflows/
│       └── test.yml
├── manage.py               # Django 管理腳本
├── requirements.txt        # Python 依賴
└── README.md               # 專案說明
```

## 核心模組說明

### 1. 資料模型層 (models.py)

#### Room（房間）
- `name`: 房間名稱
- `standard_line_score`: 每一條線總分 (L)，自動計算
- `created_at`, `updated_at`: 時間戳記

#### Member（成員）
- `room`: 外鍵關聯 Room
- `name`: 成員名稱（同一房間內唯一）
- `is_custom_calc`: 是否為客製化組
- `total_score`: 總分（自動計算）

#### Route（路線）
- `room`: 外鍵關聯 Room
- `name`: 路線名稱
- `grade`: 難度等級（V1-V8+）
- `photo`: 照片文件（ImageField）
- `photo_url`: 照片網址（舊版，已棄用）

#### Score（成績）
- `member`: 外鍵關聯 Member
- `route`: 外鍵關聯 Route
- `is_completed`: 是否完成
- `score_attained`: 獲得的分數（自動計算）

#### 核心計分函數
- `update_scores(room_id)`: 核心計分邏輯
- `calculate_standard_line_score()`: 計算每一條線總分
- `update_standard_line_score()`: 更新標準線分數

### 2. API 層 (views.py + serializers.py)

#### ViewSets
- **RoomViewSet**: 房間 CRUD 操作
  - `create`: 創建房間
  - `update`: 更新房間
  - `leaderboard`: 獲取排行榜
  - `create_route`: 創建路線

- **MemberViewSet**: 成員 CRUD 操作
  - `create`: 創建成員
  - `update`: 更新成員
  - `destroy`: 刪除成員

- **RouteViewSet**: 路線 CRUD 操作
  - `retrieve`: 獲取路線詳情
  - `update`: 更新路線
  - `destroy`: 刪除路線

- **ScoreViewSet**: 成績 CRUD 操作
  - `update`: 更新成績狀態

#### Serializers
- **RoomSerializer**: 房間序列化
- **MemberSerializer**: 成員序列化（包含名稱唯一性驗證）
- **RouteSerializer**: 路線序列化（包含照片 URL）
- **RouteCreateSerializer**: 創建路線序列化（支持批量創建成績）
- **RouteUpdateSerializer**: 更新路線序列化
- **ScoreSerializer**: 成績序列化

### 3. 視圖層 (views.py)

#### 頁面視圖
- `index_view`: 首頁（房間列表）
- `leaderboard_view`: 排行榜頁面
- `rules_view`: 規則說明頁面

### 4. 路由配置

#### 主路由 (climbing_system/urls.py)
```
/                    → index_view (首頁)
/leaderboard/<id>/   → leaderboard_view (排行榜)
/rules/              → rules_view (規則說明)
/api/                → scoring.urls (API 路由)
```

#### API 路由 (scoring/urls.py)
```
/api/rooms/                    → RoomViewSet (列表、創建)
/api/rooms/<id>/               → RoomViewSet (詳情、更新、刪除)
/api/rooms/<id>/leaderboard/   → RoomViewSet.leaderboard
/api/rooms/<id>/routes/         → RoomViewSet.create_route
/api/members/                   → MemberViewSet (列表、創建)
/api/members/<id>/              → MemberViewSet (詳情、更新、刪除)
/api/routes/                    → RouteViewSet (列表)
/api/routes/<id>/               → RouteViewSet (詳情、更新、刪除)
/api/scores/                    → ScoreViewSet (列表)
/api/scores/<id>/               → ScoreViewSet (詳情、更新、刪除)
```

## 前端架構

### 模板系統
- **base.html**: 基礎模板（導航欄、頁腳）
- **index.html**: 房間列表頁面
  - 創建新房間
  - 顯示現有房間列表
  - 自動生成房間名稱範例

- **leaderboard.html**: 排行榜頁面
  - 顯示成員排行榜
  - 路線列表與完成狀態
  - 成員管理（新增、編輯、刪除）
  - 路線管理（新增、編輯、刪除）
  - 照片上傳功能

- **rules.html**: 規則說明頁面
  - 計分規則說明
  - 一般組 vs 客製化組說明

### 前端技術
- **HTML5**: 語義化標籤
- **CSS3**: 響應式設計
- **JavaScript (Vanilla)**: 
  - Fetch API 進行 API 調用
  - FormData 處理文件上傳
  - 動態 DOM 操作
  - 模態框管理

## 資料庫架構

### 關聯關係
```
Room (1) ──→ (N) Member
Room (1) ──→ (N) Route
Member (1) ──→ (N) Score
Route (1) ──→ (N) Score
```

### 索引
- `Member.name` + `Member.room`: 唯一性約束（同一房間內名稱唯一）

### 自動計算欄位
- `Room.standard_line_score`: 根據一般組成員數自動計算
- `Member.total_score`: 根據完成路線自動計算
- `Score.score_attained`: 根據完成狀態和計分規則自動計算

## 計分邏輯

### 標準線分數 (L) 計算
1. **成員數 < 8**: `L = LCM(1, 2, ..., N)`（N 為一般組成員數）
2. **成員數 ≥ 8**: `L = 1000`（固定值）
3. **無一般組成員**: `L = 1`（預設值）

### 一般組計分
- 路線分數: `S_r = L / P_r`（P_r 為完成該路線的一般組人數）
- 總分: 所有完成路線的分數總和

### 客製化組計分
- 每完成一條路線: 固定獲得 `L` 分
- 總分: `完成路線數 × L`

### 觸發時機
- 新增/更新/刪除路線
- 更新成績狀態
- 新增/更新/刪除成員
- 修改成員組別

## 測試架構

### 測試模組結構
```
scoring/tests/
├── __init__.py
├── test_api.py                    # API 測試
│   └── APITestCase
│       ├── test_get_leaderboard
│       ├── test_create_route
│       ├── test_update_score
│       └── test_create_room_add_member_create_route
└── test_case_01_default_member.py # 計分邏輯測試
    └── TestCase1To10
        └── test_case_1_to_10
```

### 測試覆蓋範圍
- API 端點測試
- 計分邏輯測試
- 資料驗證測試
- 完整流程測試

### CI/CD
- **GitHub Actions**: 自動運行測試
  - Python 版本: 3.8, 3.9, 3.10, 3.11, 3.12
  - 測試套件: `scoring.tests`
  - 特定測試案例: `test_create_room_add_member_create_route`

## 靜態文件與媒體

### 靜態文件
- **位置**: `static/`
- **用途**: CSS、JavaScript
- **服務**: Django 開發服務器自動處理

### 媒體文件
- **位置**: `media/route_photos/`
- **用途**: 路線照片
- **配置**: `settings.MEDIA_URL`, `settings.MEDIA_ROOT`

## 安全配置

### CORS 設置
- 使用 `django-cors-headers` 處理跨域請求
- 開發環境允許所有來源

### CSRF 保護
- Django 內建 CSRF 中間件
- API 使用 Session 認證（開發環境）

## 部署架構

### 開發環境
- **伺服器**: Django 開發服務器
- **資料庫**: SQLite（預設）
- **靜態文件**: Django 自動處理

### 生產環境建議
- **WSGI 伺服器**: Gunicorn 或 uWSGI
- **反向代理**: Nginx
- **資料庫**: MySQL 或 PostgreSQL
- **靜態文件**: Nginx 或 CDN
- **媒體文件**: 雲存儲（如 AWS S3）

## 依賴管理

### 核心依賴
- `Django>=4.2.0`: Web 框架
- `djangorestframework>=3.14.0`: API 框架
- `Pillow>=10.0.0`: 圖片處理
- `django-cors-headers>=3.14.0`: CORS 支持

### 資料庫依賴（可選）
- `mysqlclient` 或 `pymysql`: MySQL 支持

## 管理命令

### init_default_data
創建預設測試數據
```bash
python manage.py init_default_data
```

## 未來擴展建議

1. **用戶認證**: 添加用戶登入/註冊功能
2. **權限管理**: 房間創建者權限
3. **即時更新**: WebSocket 支持
4. **數據導出**: Excel/PDF 導出功能
5. **統計分析**: 路線完成率、難度分布等
6. **多語言支持**: i18n 國際化

