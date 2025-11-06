# 系統設置指南

## 快速開始

### 1. 創建虛擬環境（推薦）

為了避免與系統 Python 包衝突，建議使用虛擬環境：

#### Windows PowerShell

```powershell
# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
.\venv\Scripts\Activate.ps1
```

#### Windows Command Prompt (CMD)

```cmd
# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
venv\Scripts\activate.bat
```

### 2. 安裝 Python 依賴

激活虛擬環境後，安裝項目依賴：

```bash
pip install -r requirements.txt
```

### 3. 配置資料庫

**✅ 好消息**：系統已預設使用 **SQLite**，無需額外配置即可運行！

#### 當前配置（SQLite - 預設）

系統已配置為使用 SQLite，這是快速測試和開發的最佳選擇：

- ✅ 無需安裝 MySQL
- ✅ 無需啟動服務
- ✅ 無需創建數據庫
- ✅ 直接運行即可

**SQLite 數據庫文件**：`db.sqlite3`（會自動創建）

#### 如需使用 MySQL（可選）

如果您的環境已有 MySQL 並想使用它：

1. **啟動 MySQL 服務**：
   ```powershell
   Get-Service -Name "*mysql*"
   Start-Service -Name "MySQL80"  # 根據您的服務名稱調整
   ```

2. **創建資料庫**：
   ```sql
   CREATE DATABASE climbing_score_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **編輯 `climbing_system/settings.py`**：
   - 註釋掉 SQLite 配置
   - 取消註釋 MySQL 配置並填入密碼

詳細說明請參考 `DATABASE_SETUP.md`

### 4. 一鍵啟動（推薦）✨

系統提供了自動啟動腳本，會自動完成：
- 數據庫遷移
- 初始化默認數據（房間和成員）
- 啟動服務器

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

**或者手動執行**：
```bash
# 運行遷移
python manage.py migrate

# 啟動服務器
python manage.py runserver
```

**注意**：所有數據（房間、成員、路線）需通過網頁界面創建。

### 5. 訪問系統

**訪問地址**：

- **首頁**: http://127.0.0.1:8000/
  - 創建新房間、查看所有房間列表
  - 🎯 **首次使用請在此頁面創建房間**
  
- **排行榜頁面**: http://127.0.0.1:8000/leaderboard/{room_id}/
  - 🎯 **這是主要使用頁面**，可以：
    - 查看排行榜（右側固定欄，可隨時查看排名變化）
    - 新增/編輯/刪除成員
    - 新增/編輯/刪除路線
    - 設定成員完成狀態
    - 查看路線列表
    - 點擊「完成條數」查看該成員完成的所有路線詳情
  - 將 `{room_id}` 替換為實際的房間 ID（創建房間後會自動跳轉）
  
- **規則說明**: http://127.0.0.1:8000/rules/
  - 查看詳細的計分規則說明
  
- **管理後台**: http://127.0.0.1:8000/admin/
  - 管理所有數據（需創建超級用戶：`python manage.py createsuperuser`）

## 測試計分邏輯

運行測試套件：

```bash
python manage.py test scoring.tests
```

運行特定測試案例：

```bash
# 測試完整流程：創建房間 -> 新增成員 -> 建立路線
python manage.py test scoring.tests.test_api.APITestCase.test_create_room_add_member_create_route

# 測試所有 API 接口
python manage.py test scoring.tests.test_api.APITestCase

# 測試核心計分邏輯
python manage.py test scoring.tests.test_case_01_default_member.TestCase1To10

# 測試路線漸進完成
python manage.py test scoring.tests.test_case_route_progressive_completion.TestCaseRouteProgressiveCompletion

# 測試路線名稱編輯
python manage.py test scoring.tests.test_case_route_name_edit.TestCaseRouteNameEdit

# 測試路線完成狀態更新
python manage.py test scoring.tests.test_case_route_update_completions.TestCaseRouteUpdateCompletions

# 測試 FormData 格式處理
python manage.py test scoring.tests.test_case_route_update_with_formdata.TestCaseRouteUpdateWithFormData

# 測試成員組別轉換
python manage.py test scoring.tests.test_case_member_group_conversion.TestCaseMemberGroupConversion

# 測試成員和路線操作
python manage.py test scoring.tests.test_case_member_route_operations.TestCaseMemberRouteOperations
```

## 開發注意事項

### 測試輔助工具

系統提供了 `scoring/tests/test_helpers.py` 模組，方便編寫測試案例：

- **`TestDataFactory`**: 提供創建測試數據的便捷方法
  - `create_room()`: 創建測試房間
  - `create_normal_members()`: 創建一般組成員
  - `create_custom_members()`: 創建客製化組成員
  - `create_route()`: 創建路線並自動創建成績記錄

- **`cleanup_test_data()`**: 統一清理測試數據（刪除房間及其相關數據）

- **`create_basic_test_setup()`**: 一鍵創建基本測試設置

**使用範例**：
```python
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data

class MyTestCase(TestCase):
    def setUp(self):
        self.room = TestDataFactory.create_room(name="測試房間")
        self.m1, self.m2 = TestDataFactory.create_normal_members(
            self.room, count=2, names=["成員1", "成員2"]
        )
        self.route = TestDataFactory.create_route(
            room=self.room, name="路線1", grade="V3",
            members=[self.m1, self.m2]
        )
    
    def tearDown(self):
        cleanup_test_data(room=self.room)
```

### 代碼規範

- 所有 debug logging 已移除，只保留核心業務邏輯
- 代碼已簡化，避免冗餘
- 測試代碼使用輔助工具模組提高可維護性
- 所有測試都在 `tearDown` 中統一清理數據
- 臨時文件和測試輸出文件已加入 `.gitignore`

### 問題修復記錄

已修復的問題記錄在 `issue_fixed/` 資料夾中，包含詳細的流程分析和修復報告。

**命名規則**：同一問題使用相同的編號（如 `issue_01`），不同類型的文檔使用不同的後綴（`flow_analysis`、`fix_report`）。

例如：
- `issue_01_create_route_completion_count_zero_flow_analysis.md` - 問題 01 的流程分析
- `issue_01_create_route_completion_count_zero_fix_report.md` - 問題 01 的修復報告

## 下一步

1. 通過管理後台創建房間和成員
2. 使用前端界面或 API 添加路線和成績
3. 查看即時更新的排行榜

