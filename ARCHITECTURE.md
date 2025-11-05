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
│   ├── migrations/         # 資料庫遷移文件
│   └── tests/              # 測試模組
│       ├── __init__.py
│       ├── test_helpers.py  # 測試輔助工具模組
│       ├── test_api.py
│       ├── test_case_01_default_member.py
│       ├── test_case_route_progressive_completion.py
│       ├── test_case_route_name_edit.py
│       ├── test_case_route_update_completions.py
│       ├── test_case_route_update_with_formdata.py
│       ├── test_case_route_photo_upload.py
│       ├── test_case_route_photo_thumbnail.py
│       └── test_case_mobile_ui.py
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
  - `create`: 創建房間（自動計算 standard_line_score，預設為 1）
  - `update`: 更新房間（自動重新計算 standard_line_score）
  - `retrieve`: 獲取房間詳情（包含路線列表和成員列表，使用 prefetch_related 優化）
  - `leaderboard`: 獲取排行榜
  - `create_route`: 創建路線（支持圖片上傳，支持初始完成狀態設置）

- **MemberViewSet**: 成員 CRUD 操作
  - `create`: 創建成員
  - `update`: 更新成員
  - `destroy`: 刪除成員
  - `completed_routes`: 獲取成員完成的路線列表（action）

- **RouteViewSet**: 路線 CRUD 操作
  - `retrieve`: 獲取路線詳情（包含照片 URL 和完成狀態，使用 prefetch_related 優化）
  - `update`: 更新路線（支持部分更新：名稱、難度、完成狀態、照片，支持 FormData）
  - `destroy`: 刪除路線

- **ScoreViewSet**: 成績 CRUD 操作
  - `update`: 更新成績狀態

#### Serializers
- **RoomSerializer**: 房間序列化（包含嵌套路線序列化）
  - 手動序列化 routes，使用 `RouteSerializer` 並傳遞 `context={'request': request}` 以生成完整的照片 URL
  - 使用 `prefetch_related('routes__scores__member', 'members')` 優化查詢
- **MemberSerializer**: 成員序列化（包含名稱唯一性驗證）
  - 驗證成員名稱在同一房間內唯一
  - 創建/更新後自動觸發 `update_scores`
- **RouteSerializer**: 路線序列化（包含照片 URL 和分數資訊）
  - 使用 `prefetch_related` 優化查詢，確保 scores 數據完整
  - `get_photo_url` 方法生成完整的照片 URL（包含域名）
  - `to_representation` 確保數據始終從數據庫最新獲取
- **RouteCreateSerializer**: 創建路線序列化
  - 使用 `CharField` 處理 `member_completions`，支持 JSON 字符串格式
  - 支持批量創建成績記錄
  - `grade` 為必填項目（`required=True`）
  - `photo` 字段支持圖片上傳（`ImageField`）
  - 自動解析 JSON 字符串為字典格式
- **RouteUpdateSerializer**: 更新路線序列化
  - 使用 `CharField` 處理 `member_completions`，支持 JSON 字符串格式
  - 支持 FormData 格式的請求（照片上傳）
  - 自動解析 JSON 字符串為字典格式
  - 支持部分更新（name、grade、member_completions、photo）
  - 更新完成狀態時自動觸發 `update_scores`
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
/api/members/<id>/completed-routes/ → MemberViewSet.completed_routes
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
  - 顯示成員排行榜（右側固定欄，可隨時查看排名變化）
  - 路線列表與完成狀態
  - 路線圖片縮圖顯示（有圖片的路線在等級後方顯示縮圖，點擊可查看大圖）
  - 成員管理（新增、編輯、刪除）
  - 路線管理（新增、編輯、刪除）
  - 照片上傳功能（支持 PNG、JPEG、HEIC 格式）
  - 點擊「完成條數」查看成員完成的路線詳情
  - 圖片大圖查看彈窗

- **rules.html**: 規則說明頁面
  - 計分規則說明
  - 一般組 vs 客製化組說明

### 前端技術
- **HTML5**: 語義化標籤
- **CSS3**: 響應式設計
  - 支持桌面端（>1200px）、平板端（768px-1200px）、手機端（<768px）、超小屏幕（<480px）
  - 移動端優化：排行榜顯示在頂部、按鈕全寬、表單輸入框字體大小優化（防止 iOS 自動縮放）
  - Flexbox 布局：兩欄布局（主內容區 + 固定排行榜側邊欄）
  - 圖片縮圖樣式：40x40px 圓角縮圖，懸停放大效果
  - 自定義滾動條樣式
  - 漸變背景和過渡動畫效果
- **JavaScript (Vanilla)**: 
  - Fetch API 進行 API 調用
  - FormData 處理文件上傳（支持圖片上傳，multipart/form-data）
  - 動態 DOM 操作
  - 模態框管理（多個模態框：新增/編輯成員、新增/編輯路線、編輯房間、查看完成路線、查看圖片大圖）
  - 移動端檢測和優化（自動檢測設備類型，動態調整表單行為）
  - 圖片縮圖顯示和點擊查看大圖功能
  - 自動聚焦功能（新增成員時自動聚焦到輸入框）
  - 房間名稱自動生成範例（格式：攀岩館名稱_YYYYMMDD挑戰賽）
  - 路線名稱自動編號（創建路線時自動生成「路線N」格式）

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
│       ├── test_create_room_add_member_create_route
│       └── test_get_member_completed_routes
├── test_case_01_default_member.py # 計分邏輯測試
│   └── TestCase1To10
│       └── test_case_1_to_10
├── test_case_route_progressive_completion.py  # 路線漸進完成測試
│   └── TestCaseRouteProgressiveCompletion
│       └── test_route_progressive_completion
├── test_case_route_name_edit.py   # 路線名稱編輯測試
│   └── TestCaseRouteNameEdit
│       ├── test_edit_route_name_without_change
│       ├── test_edit_route_name_change_to_number
│       ├── test_edit_route_name_change_to_text
│       ├── test_edit_route_name_remove_prefix_in_request
│       ├── test_retrieve_route_returns_correct_name
│       └── test_retrieve_route_with_text_name
├── test_case_route_update_completions.py  # 路線完成狀態更新測試
│   └── TestCaseRouteUpdateCompletions
│       ├── test_update_route_mark_two_members_completed
│       ├── test_update_route_unmark_completed_members
│       ├── test_update_route_partial_member_completions
│       ├── test_update_route_with_empty_member_completions
│       ├── test_update_route_with_json_string_member_completions
│       └── test_update_route_verify_scores_updated
├── test_case_route_update_with_formdata.py   # FormData 格式測試
│   └── TestCaseRouteUpdateWithFormData
│       ├── test_update_route_with_formdata_mark_two_members
│       ├── test_update_route_with_formdata_unmark_members
│       ├── test_update_route_with_formdata_partial_checkboxes
│       └── test_update_route_verify_api_response
├── test_case_route_photo_upload.py           # 路線圖片上傳測試
│   └── TestCaseRoutePhotoUpload
│       ├── test_create_route_with_photo
│       ├── test_create_route_without_photo
│       ├── test_update_route_add_photo
│       ├── test_update_route_replace_photo
│       ├── test_update_route_remove_photo
│       └── test_get_route_with_photo_url
├── test_case_route_photo_thumbnail.py        # 路線圖片縮圖顯示測試
│   └── TestCaseRoutePhotoThumbnail
│       ├── test_route_list_shows_photo_thumbnail
│       ├── test_route_list_no_thumbnail_for_route_without_photo
│       ├── test_route_thumbnail_after_photo_update
│       └── test_multiple_routes_with_and_without_photos
└── test_case_mobile_ui.py                    # 手機版界面測試
    └── TestCaseMobileUI
        ├── test_mobile_viewport_meta_tag
        ├── test_mobile_leaderboard_page_loads
        ├── test_mobile_api_responses
        ├── test_mobile_create_route_with_formdata
        ├── test_mobile_create_route_with_photo_detailed
        ├── test_mobile_update_route_add_photo
        ├── test_mobile_update_route_replace_photo
        ├── test_mobile_photo_upload_different_formats (PNG, JPEG, HEIC)
        ├── test_mobile_photo_upload_verify_url
        ├── test_mobile_update_route
        ├── test_mobile_get_member_completed_routes
        ├── test_mobile_responsive_layout_elements
        ├── test_mobile_css_media_queries_referenced
        └── test_mobile_form_input_font_size
```

### 測試輔助工具 (`test_helpers.py`)

提供可重用的測試數據創建和清理函數：

- **`TestDataFactory`** 類：
  - `create_room()`: 創建測試房間
  - `create_normal_members()`: 創建一般組成員
  - `create_custom_members()`: 創建客製化組成員
  - `create_route()`: 創建路線並自動創建成績記錄
  - `create_route_with_scores()`: 根據配置創建路線和成績記錄

- **`cleanup_test_data()`**: 清理測試數據（刪除房間及其相關數據）

- **`create_basic_test_setup()`**: 一鍵創建基本測試設置（房間 + 成員）

所有測試文件都使用這些輔助工具來簡化測試代碼，並在 `tearDown` 中統一清理測試數據。

### 測試覆蓋範圍
- **API 端點測試**: 獲取排行榜、創建路線、更新成績狀態、獲取成員完成的路線列表
- **計分邏輯測試**: 分數計算、完成狀態更新、成員組別處理
- **資料驗證測試**: 成員名稱唯一性、路線難度必填、JSON 格式驗證
- **完整流程測試**: 創建房間、新增成員、建立路線的完整流程
- **路線管理測試**: 路線名稱編輯、完成狀態更新、FormData 處理
- **圖片功能測試**: 圖片上傳、圖片縮圖顯示、圖片格式支持（PNG、JPEG、HEIC）
- **手機端測試**: 響應式設計、移動端 API 調用、移動端圖片上傳
- **邊界條件測試**: 空完成狀態、部分更新、漸進式完成

**總測試數量：52 個測試**

### CI/CD
- **GitHub Actions**: 自動運行測試
  - Python 版本: 3.8, 3.9, 3.10, 3.11, 3.12
  - 測試套件: `scoring.tests`
  - 特定測試案例: `scoring.tests.test_api.APITestCase.test_create_room_add_member_create_route`

## 靜態文件與媒體

### 靜態文件
- **位置**: `static/`
- **用途**: CSS、JavaScript
- **服務**: Django 開發服務器自動處理

### 媒體文件
- **位置**: `media/route_photos/`
- **用途**: 路線照片（支持 PNG、JPEG、HEIC 格式）
- **配置**: `settings.MEDIA_URL`, `settings.MEDIA_ROOT`
- **處理**: 使用 `Pillow` 庫進行圖片驗證和處理
- **URL 生成**: 通過 `RouteSerializer.get_photo_url` 生成完整的訪問 URL

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

## 數據創建

所有數據（房間、成員、路線）需通過網頁界面創建：
- **首頁** (`/`): 創建房間
- **排行榜頁面** (`/leaderboard/{room_id}/`): 新增成員、創建路線
- **管理後台** (`/admin/`): 管理所有數據（需創建超級用戶：`python manage.py createsuperuser`）

**注意**：系統不提供命令列初始化數據的功能，所有數據必須通過網頁界面創建。

## 未來擴展建議

1. **用戶認證**: 添加用戶登入/註冊功能
2. **權限管理**: 房間創建者權限
3. **即時更新**: WebSocket 支持
4. **數據導出**: Excel/PDF 導出功能
5. **統計分析**: 路線完成率、難度分布等
6. **多語言支持**: i18n 國際化

