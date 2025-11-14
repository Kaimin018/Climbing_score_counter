# 攀岩計分系統

基於「路線總分固定」邏輯的即時排行榜應用系統。

**[English](README_EN.md)** | **中文**

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
- **圖片處理**: Pillow（支持手機照片上傳，包括 HEIC 格式）
- **HTML 解析**: BeautifulSoup4（用於測試中的 HTML 結構檢查）
- **PDF 生成**: ReportLab（用於導出排行榜 PDF，可選）
- **生產環境**: Gunicorn + Nginx（AWS EC2 部署）

## 部署

### AWS EC2 部署

系統已配置支持 AWS EC2 部署，使用 Gunicorn + Nginx + SQLite 架構。

詳細部署指南請參考：
- `Deployment/docs/setup/SSH_SETUP.md` - SSH 連接配置指南（**首次部署必讀**）
- `Deployment/docs/setup/DOMAIN_SSL_GUIDE.md` - 域名綁定與 SSL 配置指南（**HTTPS 必讀**）
- `Deployment/docs/guides/AWS_EC2_DEPLOYMENT.md` - 完整部署指南
- `Deployment/docs/guides/DEPLOYMENT_CI_CD.md` - CI/CD 自動部署指南
- `Deployment/docs/troubleshooting/TROUBLESHOOTING_DEPLOYMENT.md` - 故障排除指南
- `Deployment/docs/setup/DATABASE_SYNC.md` - 數據庫同步指南（**重要**：避免更新時數據丟失）
- `Deployment/QUICK_START.md` - 快速參考
- `Deployment/docs/guides/DEPLOYMENT_CHANGES.md` - 部署修改總結
- `Deployment/INDEX.md` - 部署文檔導航索引（**推薦查看**）

**部署路徑**: `/var/www/Climbing_score_counter`

**更新方式**：
- ✅ 使用 Git：`git pull` 或 `deploy.sh` 腳本（**不需要重新 clone**）
- ✅ 使用 CI/CD：推送到 main/master 分支自動部署

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
   - ✅ 啟動服務器

3. **訪問系統**：
   - **首頁**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
     - 未登錄：顯示登錄/註冊界面（桌面版：兩欄布局，移動版：單欄布局）
     - 已登錄：顯示房間列表，可創建新房間
   - **排行榜頁面**: [http://127.0.0.1:8000/leaderboard/{room_id}/](http://127.0.0.1:8000/leaderboard/{room_id}/)（管理成員、路線、查看排行榜）
   - **規則說明**: [http://127.0.0.1:8000/rules/](http://127.0.0.1:8000/rules/)（查看計分規則說明）
   - **管理後台**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
   
   **登錄方式**：
   - 用戶註冊/登錄：需要用戶名和密碼（密碼需符合強度要求）
   - 訪客登錄：無需註冊，一鍵登錄即可使用系統功能

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
4. 啟動服務器

**注意**：
- 所有數據（房間、成員、路線）需通過網頁界面創建，系統不提供命令列初始化數據的功能
- 首次訪問需要登錄（註冊帳號或使用訪客登錄）
- 訪客登錄無需註冊，可直接使用系統功能

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

### 更新成員

```
PATCH /api/members/{member_id}/
```

請求體格式：
```json
{
  "name": "新成員名稱",
  "is_custom_calc": true
}
```

**注意**：
- 可以只更新部分欄位（name、is_custom_calc）
- 更新成員名稱時，仍需確保在同一房間內唯一
- 修改成員組別（is_custom_calc）會自動觸發計分更新

### 刪除成員

```
DELETE /api/members/{member_id}/
```

刪除成員後會自動觸發計分更新。

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
- 支持照片上傳（手機可直接拍照）

### 更新路線

```
PATCH /api/routes/{route_id}/
```

請求體格式（JSON）：
```json
{
  "name": "路線1",
  "grade": "V5",
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
grade: V5
photo: [文件]
member_completions: {"1":true,"2":false,"3":true}
```

**注意**：
- 可以只更新部分欄位（name、grade、member_completions、photo）
- `member_completions` 為 JSON 字符串格式，鍵為成員 ID（字符串），值為布林值
- 未在 `member_completions` 中指定的成員，其完成狀態會被設為 `false`
- 支持照片更新（上傳新照片會覆蓋舊照片）

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

### 導出排行榜 PDF

```
GET /api/rooms/{room_id}/export-pdf/
```

**注意**：
- 需要安裝 `reportlab` 庫：`pip install reportlab`
- 返回 PDF 文件，包含排行榜數據、路線照片和成員完成狀態
- 支持中文字體顯示

### 刪除路線

```
DELETE /api/routes/{route_id}/
```

刪除路線後會自動觸發計分更新。

## 管理命令

系統提供以下 Django 管理命令：

### 清理未使用的照片

```bash
python manage.py cleanup_unused_photos
```

此命令會掃描 `media/route_photos/` 目錄下的所有照片文件，檢查是否有對應的路線記錄。如果沒有對應的路線，則刪除該照片文件。

**可選參數**：
- `--dry-run`: 只顯示將要刪除的文件，不實際刪除
- `--verbose`: 顯示詳細信息

**使用場景**：
- 定期清理未使用的照片文件，釋放存儲空間
- 在刪除路線後清理對應的照片文件

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
# 運行所有測試
python manage.py test scoring.tests

# 運行特定測試案例
python manage.py test scoring.tests.test_api.APITestCase.test_create_room_add_member_create_route
```

### 測試案例

系統包含以下測試案例（共 36 個測試文件，超過 300 個測試用例）：

**注意**：詳細的測試文件列表請參考 `ARCHITECTURE.md` 文檔。

1. **核心計分邏輯測試**（`test_case_01_default_member.py`）：
   - 循序漸進新增路線的計分
   - 標記完成/未完成狀態的計分更新
   - 刪除路線後的計分重算
   - 客製化組與常態組的分數獨立計算

2. **API 接口測試**（`test_api.py`）：
   - 獲取排行榜
   - 創建路線
   - 更新成績狀態
   - 完整流程測試（創建房間、新增成員、建立路線）
   - 獲取成員完成的路線列表

3. **路線漸進完成測試**（`test_case_route_progressive_completion.py`）：
   - 路線建立時無人完成
   - 後來有一人完成
   - 後來再有一人完成
   - 驗證完成人數和分數計算

4. **路線名稱編輯測試**（`test_case_route_name_edit.py`）：
   - 編輯路線名稱（不變更）
   - 編輯路線名稱（改為數字）
   - 編輯路線名稱（改為文字）
   - 驗證 API 返回的路線名稱正確性

5. **路線完成狀態更新測試**（`test_case_route_update_completions.py`）：
   - 標記兩個成員為完成
   - 取消標記已完成成員
   - 部分成員完成狀態更新
   - 空完成狀態處理
   - 驗證分數更新

6. **FormData 格式測試**（`test_case_route_update_with_formdata.py`）：
   - 使用 FormData 標記成員完成
   - 使用 FormData 取消標記
   - 部分勾選框的 FormData 處理
   - 驗證 API 響應結構

7. **創建路線完整流程測試**（`test_api.py`）：
   - 創建路線時選擇多個完成人員
   - 驗證前端顯示的完成人數正確
   - 模擬完整的前端流程（創建 → 立即刷新）

8. **路線圖片上傳測試**（`test_case_route_photo_upload.py`）：
   - 創建路線時上傳圖片
   - 創建路線時不上傳圖片
   - 更新路線時添加圖片
   - 更新路線時替換圖片
   - 更新路線時移除圖片
   - 獲取路線時 photo_url 正確返回

9. **路線圖片縮圖顯示測試**（`test_case_route_photo_thumbnail.py`）：
   - 路線列表中有圖片的路線顯示縮圖
   - 沒有圖片的路線不顯示縮圖
   - 更新路線圖片後縮圖更新
   - 多個路線（有圖片和無圖片）同時存在時縮圖顯示正確

10. **手機版界面測試**（`test_case_mobile_ui.py`）：
   - 頁面包含 viewport meta 標籤
   - 手機端排行榜頁面可以正常載入
   - 手機端 API 響應正常
   - 手機端使用 FormData 創建路線（模擬手機上傳）
   - 手機端創建路線時上傳圖片（詳細驗證）
   - 手機端更新路線時添加圖片（原本沒有圖片）
   - 手機端更新路線時替換圖片（原本有圖片）
   - 手機端上傳不同格式的圖片（PNG、JPEG、HEIC）
   - 手機端上傳圖片後，photo_url 正確返回（測試多種手機瀏覽器）
   - 手機端更新路線
   - 手機端獲取成員完成的路線列表
   - 手機端頁面包含響應式設計所需的元素
   - CSS 文件包含移動端媒體查詢
   - 手機端表單輸入框字體大小（防止 iOS 自動縮放）

11. **安全性測試**（`test_case_12_security.py`）：
   - 用戶認證（註冊、登錄、登出、當前用戶、XSS/SQL 注入防護）
   - API 權限控制（讀取/寫入權限、刪除權限）
   - XSS 攻擊防護（房間名、成員名、路線名、難度等級、JSON 字段、郵箱）
   - SQL 注入防護（房間名、成員名、路線名、URL 參數、查詢參數）

12. **設置配置測試**（`test_case_13_settings_config.py`）：
    - 日誌配置（開發/生產環境）
    - 權限配置（開發/生產環境）
    - 環境變數配置

13. **登錄界面功能測試**（`test_case_14_login_ui.py`）：
    - 登錄/註冊表單功能
    - 密碼驗證
    - 訪客登錄
    - CSRF 處理
    - 用戶狀態管理

14. **AWS 部署問題測試**（`test_case_15_aws_deployment_issues.py`）

15. **iPhone 照片上傳測試**（`test_case_16_iphone_photo_upload.py`）

16. **移動端照片上傳測試**（`test_case_17_mobile_photo_upload.py`）

17. **路線照片顯示測試**（`test_case_18_route_photo_display.py`）

18. **移動端刪除路線測試**（`test_case_19_mobile_delete_route.py`）

19. **首次使用相機拍照測試**（`test_case_20_first_time_camera_photo.py`）

20. **移動端桌面端數據一致性測試**（`test_case_21_mobile_desktop_data_consistency.py`）

21. **iPhone 照片更新路線修復測試**（`test_case_22_iphone_photo_update_route_fix.py`）

22. **桌面端路線更新認證測試**（`test_case_23_desktop_route_update_authentication.py`）

23. **成員刪除排行榜測試**（`test_case_24_member_deletion_leaderboard.py`）

24. **訪客創建房間 CSRF 測試**（`test_case_25_guest_create_room_csrf.py`）

25. **創建路線並上傳照片測試**（`test_case_26_create_route_with_photo.py`）

26. **房間刪除測試**（`test_case_27_room_deletion.py`）

27. **標籤頁切換測試**（`test_case_27_tab_switching.py`）

28. **邊界值測試**（`test_case_28_boundary_values.py`）

29. **Safari 路線列表對齊測試**（`test_case_28_safari_route_list_alignment.py`）：
   - Safari 瀏覽器路線列表左對齊
   - 路線名稱不會意外換行
   - 整個路線列表框架左對齊

30. **數據完整性測試**（`test_case_29_data_integrity.py`）

31. **Safari 詳細對齊診斷測試**（`test_case_29_safari_detailed_alignment.py`）：
   - 詳細檢查每個元素的 CSS 屬性值
   - 檢查 HTML 結構和內聯樣式
   - 檢查 JavaScript 生成的 HTML
   - 檢查移動端特定的樣式覆蓋
   - 檢查 Safari 特定的兼容性問題（包括 -webkit- 前綴）

32. **向現有路線添加成員測試**（`test_case_30_add_member_to_existing_routes.py`）

33. **創建路線並勾選成員測試**（`test_case_31_create_route_with_checked_members.py`）

34. **BufferedRandom Pickle 修復測試**（`test_case_32_buffered_random_pickle_fix.py`）

35. **壓力測試：100 條路線帶照片**（`test_case_33_stress_test_100_routes_with_photos.py`）

36. **訪客權限限制測試**（`test_case_34_guest_permission_restrictions.py`）

37. **PDF 導出功能測試**（`test_case_35_pdf_export.py`）

38. **iPhone 截圖上傳測試**（`test_case_iphone_screenshot_upload.py`）

### GitHub Actions 測試

項目已配置 GitHub Actions 自動測試，每次推送代碼時會自動運行測試。詳見 `.github/workflows/test.yml`。

測試會在多個 Python 版本（3.8, 3.9, 3.10, 3.11, 3.12）上運行，確保兼容性。

## 開發與維護

### 管理後台

訪問 `/admin/` 可以使用 Django 管理後台管理所有數據。

**首次使用**：需要創建超級用戶：
```bash
python manage.py createsuperuser
```

### 添加測試數據

所有數據需通過網頁界面創建：
- **首頁** (`/`): 創建房間
- **排行榜頁面** (`/leaderboard/{room_id}/`): 新增成員、創建路線
- **管理後台** (`/admin/`): 管理所有數據

**注意**：系統不提供命令列初始化數據的功能，所有數據必須通過網頁界面創建。

### 問題修復記錄

已修復的問題記錄在 `issue_fixed/` 資料夾中：
- `issue_01_create_route_completion_count_zero_flow_analysis.md` - 詳細流程分析
- `issue_01_create_route_completion_count_zero_fix_report.md` - 修復報告
- `issue_02_logging_and_permission_config_fix_report.md` - 日誌和權限配置修復報告
- `issue_02_logging_and_permission_config_flow_analysis.md` - 日誌和權限配置流程分析

**命名規則**：同一問題使用相同的編號（如 `issue_01`、`issue_02`），不同類型的文檔使用不同的後綴（`flow_analysis`、`fix_report`）。

### 測試輔助工具

系統提供了 `scoring/tests/test_helpers.py` 模組，包含可重用的測試數據創建、配置檢查和斷言函數：

- **數據創建**：
  - `TestDataFactory`: 提供創建房間、成員、路線的便捷方法
  - `cleanup_test_data()`: 統一清理測試數據（刪除房間及其相關數據）
  - `create_basic_test_setup()`: 一鍵創建基本測試設置

- **配置檢查**：
  - `is_allow_any_permission()`: 檢查當前環境是否使用 AllowAny 權限
  - `is_debug_mode()`: 檢查當前是否為開發模式
  - `should_allow_unauthenticated_access()`: 檢查當前環境是否應該允許未認證訪問
  - `get_logging_handlers()`: 獲取當前日誌配置的 handlers
  - `has_file_logging()`: 檢查當前是否配置了文件日誌

- **測試斷言**：
  - `assert_response_status_for_permission()`: 根據當前權限配置驗證響應狀態碼

所有測試都在 `tearDown` 方法中使用 `cleanup_test_data()` 確保測試後數據清理乾淨。

### 代碼規範

- 測試代碼使用輔助工具模組提高可維護性
- 臨時文件和測試輸出文件已加入 `.gitignore`

## 許可證

本專案僅供學習與開發使用。

