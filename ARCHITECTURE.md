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
│   ├── auth_views.py       # 認證視圖（註冊、登錄、登出、訪客登錄）
│   ├── auth_serializers.py # 認證序列化器
│   ├── serializers.py      # API 序列化器
│   ├── permissions.py      # 權限控制
│   ├── urls.py             # API 路由
│   ├── admin.py            # Django Admin 配置
│   ├── management/         # 管理命令
│   │   └── commands/
│   ├── migrations/         # 資料庫遷移文件
│   └── tests/              # 測試模組
│       ├── __init__.py
│       ├── test_helpers.py  # 測試輔助工具模組
│       ├── test_case_01_default_member.py
│       ├── test_case_02_api.py
│       ├── test_case_03_route_progressive_completion.py
│       ├── test_case_04_route_name_edit.py
│       ├── test_case_05_route_update_completions.py
│       ├── test_case_06_route_update_with_formdata.py
│       ├── test_case_07_route_photo_upload.py
│       ├── test_case_08_route_photo_thumbnail.py
│       ├── test_case_09_member_group_conversion.py
│       ├── test_case_10_member_route_operations.py
│       ├── test_case_11_mobile_ui.py
│       ├── test_case_12_security.py
│       ├── test_case_13_settings_config.py
│       ├── test_case_14_login_ui.py
│       ├── test_case_15_aws_deployment_issues.py
│       ├── test_case_16_iphone_photo_upload.py
│       ├── test_case_17_mobile_photo_upload.py
│       ├── test_case_18_route_photo_display.py
│       ├── test_case_19_mobile_delete_route.py
│       ├── test_case_20_first_time_camera_photo.py
│       ├── test_case_21_mobile_desktop_data_consistency.py
│       ├── test_case_22_iphone_photo_update_route_fix.py
│       ├── test_case_23_desktop_route_update_authentication.py
│       ├── test_case_24_member_deletion_leaderboard.py
│       ├── test_case_25_guest_create_room_csrf.py
│       ├── test_case_26_create_route_with_photo.py
│       ├── test_case_27_room_deletion.py
│       ├── test_case_27_tab_switching.py
│       ├── test_case_28_boundary_values.py
│       ├── test_case_29_data_integrity.py
│       └── test_case_30_add_member_to_existing_routes.py
├── templates/              # HTML 模板
│   ├── base.html           # 基礎模板（導航欄、頁腳）
│   ├── index.html          # 首頁（登錄界面/房間列表）
│   ├── login.html          # 登錄頁面（已棄用，功能已整合到 index.html）
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
- `index_view`: 首頁（登錄界面/房間列表）
- `leaderboard_view`: 排行榜頁面
- `rules_view`: 規則說明頁面

#### 認證視圖 (auth_views.py)
- `register_view`: 用戶註冊（POST /api/auth/register/）
- `login_view`: 用戶登錄（POST /api/auth/login/）
- `guest_login_view`: 訪客登錄（POST /api/auth/guest-login/）
- `logout_view`: 用戶登出（POST /api/auth/logout/）
- `current_user_view`: 獲取當前用戶信息（GET /api/auth/current-user/）

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
/api/auth/register/             → register_view (用戶註冊)
/api/auth/login/                → login_view (用戶登錄)
/api/auth/guest-login/          → guest_login_view (訪客登錄)
/api/auth/logout/               → logout_view (用戶登出)
/api/auth/current-user/         → current_user_view (獲取當前用戶)
```

## 前端架構

### 模板系統
- **base.html**: 基礎模板（導航欄、頁腳）
- **index.html**: 首頁（登錄界面/房間列表）
  - 未登錄：顯示登錄/註冊界面（桌面版：兩欄布局，移動版：單欄布局）
  - 已登錄：顯示房間列表，可創建新房間
  - 自動生成房間名稱範例
  - 登錄/註冊表單切換
  - 實時密碼強度驗證
  - 訪客登錄功能

- **login.html**: 登錄頁面（已棄用，功能已整合到 index.html）

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
  - **桌面版登錄界面**：兩欄布局（左側品牌展示區，右側表單區）
    - 品牌區域：漸變背景、品牌圖標、功能特點列表
    - 表單區域：登錄/註冊切換、密碼規則驗證、訪客登錄
    - 最大寬度 1000px，圓角卡片設計
  - **移動版登錄界面**：單欄布局，隱藏品牌區域
- **JavaScript (Vanilla)**: 
  - Fetch API 進行 API 調用
  - **CSRF Token 處理**：所有 POST/PATCH/DELETE 請求自動包含 CSRF token
  - FormData 處理文件上傳（支持圖片上傳，multipart/form-data）
  - 動態 DOM 操作
  - **登錄界面功能**：
    - 登錄/註冊表單切換
    - 實時密碼強度驗證（8 字符、大小寫、數字、特殊字符）
    - 密碼匹配驗證
    - 訪客登錄功能
    - 用戶認證狀態檢查和導航欄更新
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
├── test_helpers.py                           # 測試輔助工具模組
│   ├── TestDataFactory                       # 測試數據工廠
│   ├── cleanup_test_data                     # 清理測試數據
│   ├── create_basic_test_setup               # 創建基本測試設置
│   ├── is_allow_any_permission               # 檢查權限配置
│   ├── is_debug_mode                         # 檢查 DEBUG 模式
│   ├── should_allow_unauthenticated_access   # 檢查是否允許未認證訪問
│   ├── assert_response_status_for_permission # 驗證響應狀態
│   ├── get_logging_handlers                  # 獲取日誌 handlers
│   └── has_file_logging                      # 檢查文件日誌配置
├── test_case_01_default_member.py           # 計分邏輯測試
│   └── TestCase1To10
│       └── test_case_1_to_10
├── test_case_02_api.py                       # API 測試
│   └── APITestCase
│       ├── test_get_leaderboard
│       ├── test_create_route
│       ├── test_update_score
│       ├── test_create_room_add_member_create_route
│       └── test_get_member_completed_routes
├── test_case_03_route_progressive_completion.py  # 路線漸進完成測試
│   └── TestCaseRouteProgressiveCompletion
│       └── test_route_progressive_completion
├── test_case_04_route_name_edit.py           # 路線名稱編輯測試
│   └── TestCaseRouteNameEdit
│       ├── test_edit_route_name_without_change
│       ├── test_edit_route_name_change_to_number
│       ├── test_edit_route_name_change_to_text
│       ├── test_edit_route_name_remove_prefix_in_request
│       ├── test_retrieve_route_returns_correct_name
│       └── test_retrieve_route_with_text_name
├── test_case_05_route_update_completions.py  # 路線完成狀態更新測試
│   └── TestCaseRouteUpdateCompletions
│       ├── test_update_route_mark_two_members_completed
│       ├── test_update_route_unmark_completed_members
│       ├── test_update_route_partial_member_completions
│       ├── test_update_route_with_empty_member_completions
│       ├── test_update_route_with_json_string_member_completions
│       └── test_update_route_verify_scores_updated
├── test_case_06_route_update_with_formdata.py   # FormData 格式測試
│   └── TestCaseRouteUpdateWithFormData
│       ├── test_update_route_with_formdata_mark_two_members
│       ├── test_update_route_with_formdata_unmark_members
│       ├── test_update_route_with_formdata_partial_checkboxes
│       └── test_update_route_verify_api_response
├── test_case_07_route_photo_upload.py        # 路線圖片上傳測試
│   └── TestCaseRoutePhotoUpload
│       ├── test_create_route_with_photo
│       ├── test_create_route_without_photo
│       ├── test_update_route_add_photo
│       ├── test_update_route_replace_photo
│       ├── test_update_route_remove_photo
│       └── test_get_route_with_photo_url
├── test_case_08_route_photo_thumbnail.py     # 路線圖片縮圖顯示測試
│   └── TestCaseRoutePhotoThumbnail
│       ├── test_route_list_shows_photo_thumbnail
│       ├── test_route_list_no_thumbnail_for_route_without_photo
│       ├── test_route_thumbnail_after_photo_update
│       └── test_multiple_routes_with_and_without_photos
├── test_case_09_member_group_conversion.py  # 成員組別轉換測試
│   └── TestCaseMemberGroupConversion
├── test_case_10_member_route_operations.py  # 成員路線操作測試
│   └── TestCaseMemberRouteOperations
├── test_case_11_mobile_ui.py                # 手機版界面測試
│   └── TestCaseMobileUI
│       ├── test_mobile_viewport_meta_tag
│       ├── test_mobile_leaderboard_page_loads
│       ├── test_mobile_api_responses
│       ├── test_mobile_create_route_with_formdata
│       ├── test_mobile_create_route_with_photo_detailed
│       ├── test_mobile_update_route_add_photo
│       ├── test_mobile_update_route_replace_photo
│       ├── test_mobile_photo_upload_different_formats (PNG, JPEG, HEIC)
│       ├── test_mobile_photo_upload_verify_url
│       ├── test_mobile_update_route
│       ├── test_mobile_get_member_completed_routes
│       ├── test_mobile_responsive_layout_elements
│       ├── test_mobile_css_media_queries_referenced
│       └── test_mobile_form_input_font_size
├── test_case_12_security.py                 # 安全性測試
│   ├── TestCaseAuthentication                # 用戶認證測試
│   │   ├── test_user_registration
│   │   ├── test_user_login
│   │   ├── test_user_logout
│   │   ├── test_current_user
│   │   ├── test_user_registration_with_xss_in_username
│   │   └── test_user_login_with_sql_injection
│   ├── TestCaseAPIPermissions                # API 權限測試
│   │   ├── test_read_without_authentication
│   │   ├── test_create_without_authentication
│   │   ├── test_update_without_authentication
│   │   ├── test_delete_requires_authentication
│   │   └── test_route_delete_requires_authentication
│   ├── TestCaseXSSProtection                 # XSS 防護測試
│   │   ├── test_xss_in_room_name
│   │   ├── test_xss_in_member_name
│   │   ├── test_xss_in_route_name
│   │   ├── test_xss_in_route_grade
│   │   ├── test_xss_in_json_member_completions
│   │   └── test_xss_in_email_field
│   └── TestCaseSQLInjectionProtection       # SQL 注入防護測試
│       ├── test_sql_injection_in_room_name
│       ├── test_sql_injection_in_member_name
│       ├── test_sql_injection_in_route_name
│       ├── test_sql_injection_in_room_id_parameter
│       └── test_sql_injection_in_filter_parameters
└── test_case_13_settings_config.py          # 設置配置測試
    ├── TestCaseLoggingConfig                 # 日誌配置測試
    ├── TestCasePermissionConfig             # 權限配置測試
    └── TestCaseEnvironmentVariables          # 環境變數測試
└── test_case_14_login_ui.py                 # 登錄界面功能測試
    └── TestCaseLoginUI
        ├── test_index_shows_login_when_not_authenticated
        ├── test_index_shows_room_list_when_authenticated
        ├── test_login_form_submission
        ├── test_login_form_validation
        ├── test_login_with_wrong_credentials
        ├── test_login_redirects_to_home_after_success
        ├── test_register_form_submission
        ├── test_register_form_validation
        ├── test_register_auto_login
        ├── test_register_with_password_mismatch
        ├── test_duplicate_username_registration
        ├── test_logout_functionality
        ├── test_navbar_shows_user_info_when_authenticated
        ├── test_navbar_hides_user_info_when_not_authenticated
        ├── test_switch_between_login_and_register_tabs
        ├── test_guest_login_functionality
        ├── test_guest_login_creates_unique_username
        ├── test_guest_login_already_guest_user
        ├── test_guest_user_can_access_rooms
        ├── test_guest_user_can_create_room
        ├── test_guest_user_can_create_member
        ├── test_guest_user_can_create_member_with_csrf
        ├── test_guest_login_button_in_template
        └── test_guest_user_complete_workflow
├── test_case_15_aws_deployment_issues.py    # AWS 部署問題測試
├── test_case_16_iphone_photo_upload.py      # iPhone 照片上傳測試
├── test_case_17_mobile_photo_upload.py      # 移動端照片上傳測試
├── test_case_18_route_photo_display.py      # 路線照片顯示測試
├── test_case_19_mobile_delete_route.py     # 移動端刪除路線測試
├── test_case_20_first_time_camera_photo.py  # 首次使用相機拍照測試
├── test_case_21_mobile_desktop_data_consistency.py  # 移動端桌面端數據一致性測試
├── test_case_22_iphone_photo_update_route_fix.py  # iPhone 照片更新路線修復測試
├── test_case_23_desktop_route_update_authentication.py  # 桌面端路線更新認證測試
├── test_case_24_member_deletion_leaderboard.py  # 成員刪除排行榜測試
├── test_case_25_guest_create_room_csrf.py  # 訪客創建房間 CSRF 測試
├── test_case_26_create_route_with_photo.py  # 創建路線並上傳照片測試
├── test_case_27_room_deletion.py           # 房間刪除測試
├── test_case_27_tab_switching.py            # 標籤頁切換測試
├── test_case_28_boundary_values.py          # 邊界值測試
├── test_case_29_data_integrity.py           # 數據完整性測試
└── test_case_30_add_member_to_existing_routes.py  # 向現有路線添加成員測試
```

### 測試輔助工具 (`test_helpers.py`)

提供可重用的測試數據創建、清理和配置檢查函數：

- **`TestDataFactory`** 類：
  - `create_room()`: 創建測試房間
  - `create_normal_members()`: 創建一般組成員
  - `create_custom_members()`: 創建客製化組成員
  - `create_route()`: 創建路線並自動創建成績記錄
  - `create_route_with_scores()`: 根據配置創建路線和成績記錄

- **數據清理函數**：
  - `cleanup_test_data()`: 清理測試數據（刪除房間及其相關數據）
  - `create_basic_test_setup()`: 一鍵創建基本測試設置（房間 + 成員）

- **配置檢查函數**：
  - `is_allow_any_permission()`: 檢查當前環境是否使用 AllowAny 權限
  - `is_debug_mode()`: 檢查當前是否為開發模式
  - `should_allow_unauthenticated_access()`: 檢查當前環境是否應該允許未認證訪問
  - `get_logging_handlers()`: 獲取當前日誌配置的 handlers
  - `has_file_logging()`: 檢查當前是否配置了文件日誌

- **測試斷言函數**：
  - `assert_response_status_for_permission()`: 根據當前權限配置驗證響應狀態碼

所有測試文件都使用這些輔助工具來簡化測試代碼，並在 `tearDown` 中統一清理測試數據。

### 測試覆蓋範圍
- **API 端點測試**: 獲取排行榜、創建路線、更新成績狀態、獲取成員完成的路線列表
- **計分邏輯測試**: 分數計算、完成狀態更新、成員組別處理
- **資料驗證測試**: 成員名稱唯一性、路線難度必填、JSON 格式驗證
- **登錄界面測試**: 登錄/註冊表單、密碼驗證、訪客登錄、CSRF 處理、用戶狀態管理
- **安全性測試**: 用戶認證、API 權限控制、XSS 防護、SQL 注入防護
- **完整流程測試**: 創建房間、新增成員、建立路線的完整流程
- **路線管理測試**: 路線名稱編輯、完成狀態更新、FormData 處理、路線刪除、房間刪除
- **圖片功能測試**: 圖片上傳、圖片縮圖顯示、圖片格式支持（PNG、JPEG、HEIC）、iPhone 照片處理
- **手機端測試**: 響應式設計、移動端 API 調用、移動端圖片上傳、移動端刪除操作
- **邊界條件測試**: 空完成狀態、部分更新、漸進式完成、邊界值測試
- **數據完整性測試**: 外鍵約束、唯一性約束、數據一致性、事務處理、並發操作
- **部署相關測試**: AWS 部署問題、認證配置、CSRF 處理
- **用戶體驗測試**: 標籤頁切換、移動端桌面端數據一致性、首次使用相機拍照
- **配置測試**: 日誌配置（開發/生產環境）、權限配置（開發/生產環境）、環境變數配置

**總測試數量：超過 150 個測試用例**（包含 30 個測試文件，涵蓋所有核心功能和邊界情況）

### CI/CD
- **GitHub Actions**: 自動運行測試
  - Python 版本: 3.8, 3.9, 3.10, 3.11, 3.12
  - 測試套件: `scoring.tests`
  - 特定測試案例: `scoring.tests.test_api.APITestCase.test_create_room_add_member_create_route`

## 靜態文件與媒體

### 靜態文件
- **位置**: `static/`
- **用途**: CSS、JavaScript
- **開發環境**: Django 開發服務器自動處理
- **生產環境**: 收集到 `staticfiles/` 目錄，由 Nginx 服務

### 媒體文件
- **位置**: `media/route_photos/`
- **用途**: 路線照片（支持 PNG、JPEG、HEIC 格式）
- **配置**: `settings.MEDIA_URL`, `settings.MEDIA_ROOT`
- **處理**: 使用 `Pillow` 庫進行圖片驗證和處理
- **URL 生成**: 通過 `RouteSerializer.get_photo_url` 生成完整的訪問 URL
- **生產環境**: 由 Nginx 直接服務媒體文件

## 日誌配置

### 開發環境（DEBUG=True）
- **Handlers**: 僅使用 `console` handler
- **輸出**: 標準輸出（控制台）
- **級別**: INFO

### 生產環境（DEBUG=False）
- **Handlers**: `console` + `file` handler
- **輸出**: 
  - 控制台（標準輸出）
  - 文件：`logs/django.log`
- **級別**: INFO
- **目錄**: 自動創建 `logs/` 目錄（如果不存在）

## 安全配置

### CORS 設置
- 使用 `django-cors-headers` 處理跨域請求
- 開發環境允許所有來源（`CORS_ALLOW_ALL_ORIGINS=True`）
- 生產環境可通過環境變數設置具體的允許來源（`CORS_ALLOWED_ORIGINS`）

### CSRF 保護
- Django 內建 CSRF 中間件
- API 使用 Session 認證（開發環境）

### 權限配置
- **開發環境**（`DEBUG=True`）:
  - REST Framework 默認權限：`AllowAny`（允許所有操作，便於測試）
  - 所有 ViewSet 使用默認權限配置
  
- **生產環境**（`DEBUG=False`）:
  - REST Framework 默認權限：`IsAuthenticatedOrReadOnly`（需要認證才能寫入）
  - 讀取操作（GET）允許未認證訪問
  - 寫入操作（POST、PUT、PATCH、DELETE）需要認證

### 環境變數配置
- `SECRET_KEY`: Django 密鑰（必須在生產環境中設置）
- `DEBUG`: 調試模式（生產環境必須設為 `False`）
- `ALLOWED_HOSTS`: 允許的主機列表（用逗號分隔）
- `CORS_ALLOW_ALL_ORIGINS`: 是否允許所有 CORS 來源（生產環境建議設為 `False`）
- `CORS_ALLOWED_ORIGINS`: 允許的 CORS 來源列表（用逗號分隔）
- `SECURE_SSL_REDIRECT`: 是否強制 HTTPS 重定向（生產環境建議設為 `True`）

## 部署架構

### 開發環境
- **伺服器**: Django 開發服務器
- **資料庫**: SQLite（預設）
- **靜態文件**: Django 自動處理
- **權限**: AllowAny（允許所有操作）
- **日誌**: Console handler

### 生產環境（AWS EC2）
- **WSGI 伺服器**: Gunicorn
- **反向代理**: Nginx
- **資料庫**: SQLite（或可選 MySQL/PostgreSQL）
- **靜態文件**: Nginx 服務 `staticfiles/` 目錄
- **媒體文件**: Nginx 服務 `media/` 目錄
- **權限**: IsAuthenticatedOrReadOnly（需要認證才能寫入）
- **日誌**: Console + File handler（`logs/django.log`）
- **進程管理**: Systemd
- **部署路徑**: `/var/www/Climbing_score_counter`

詳細部署指南請參考：`Deployment/AWS_EC2_DEPLOYMENT.md`

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


## 已實現功能

### 1. 用戶認證系統 ✓
- **註冊功能**: `POST /api/auth/register/` - 用戶註冊，支持密碼強度驗證
  - 密碼規則：至少 8 個字符，包含大寫、小寫、數字和特殊字符
  - 實時密碼驗證和視覺反饋
- **登錄功能**: `POST /api/auth/login/` - Session 認證
- **訪客登錄**: `POST /api/auth/guest-login/` - 無需註冊的訪客模式
  - 自動創建唯一訪客用戶名（格式：`guest_{timestamp}_{random}`）
  - 目前權限與普通用戶相同，後續可調整
- **登出功能**: `POST /api/auth/logout/` - 安全登出
- **當前用戶**: `GET /api/auth/current-user/` - 獲取當前登錄用戶信息
- **安全防護**: XSS 和 SQL 注入防護已集成到認證流程中
- **CSRF 保護**: 所有 POST/PATCH/DELETE 請求都包含 CSRF token
- **相關文件**: `scoring/auth_views.py`, `scoring/auth_serializers.py`
- **測試覆蓋**: 
  - `test_case_12_security.py` - 安全性測試（XSS、SQL 注入、權限控制）
  - `test_case_14_login_ui.py` - 登錄界面功能測試（24 個測試用例）

### 2. API 權限控制 ✓
- **讀取權限**: 未認證用戶可以讀取數據（查看房間、排行榜等）
- **寫入權限**: 創建、更新、刪除操作需要認證（生產環境）
- **開發環境**: 使用 `AllowAny` 權限，便於開發和測試
- **生產環境**: 使用 `IsAuthenticatedOrReadOnly` 權限，確保安全性
- **相關文件**: `climbing_system/settings.py` (REST_FRAMEWORK 配置)

## 未來擴展建議

### 1. 權限管理增強
- **房間創建者權限**: 為 Room 模型添加 `created_by` 字段，實現房間創建者專屬權限
  - 已有 `IsOwnerOrReadOnly` 權限類（`scoring/permissions.py`），但需要模型支持
  - 允許房間創建者管理自己創建的房間（編輯、刪除）
  - 其他用戶只能查看和參與

### 2. 即時更新功能
- **WebSocket 支持**: 實現實時排行榜更新
  - 使用 Django Channels 或類似技術
  - 當路線完成狀態改變時，自動推送更新給所有在線用戶
  - Nginx 配置中已預留 WebSocket 支持註釋

### 3. 數據導出功能
- **Excel 導出**: 導出排行榜、路線完成記錄等
  - 使用 `openpyxl` 或 `xlsxwriter` 庫
  - 支持自定義格式和樣式
- **PDF 導出**: 生成比賽報告、統計圖表
  - 使用 `reportlab` 或 `weasyprint` 庫
  - 支持包含圖片的完整報告

### 4. 統計分析功能
- **路線完成率統計**: 計算每條路線的完成率
- **難度分布分析**: 統計不同難度等級的路線分布
- **成員表現分析**: 分析成員的完成趨勢和進步情況
- **時間序列分析**: 追蹤分數變化趨勢
- **可視化圖表**: 使用 Chart.js 或類似庫生成圖表

### 5. 多語言支持
- **i18n 國際化**: Django 已配置 `USE_I18N = True`
  - 需要創建翻譯文件（`.po` 文件）
  - 支持中文、英文等多種語言
  - 前端界面也需要支持多語言切換

### 6. 其他擴展建議
- **移動端應用**: 開發原生移動應用（React Native 或 Flutter）
- **推送通知**: 實現比賽開始、結果更新等推送通知
- **社交功能**: 添加評論、分享等功能
- **歷史記錄**: 保存歷史比賽記錄，支持回放和分析
- **批量操作**: 支持批量導入成員、批量創建路線等

