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

#### 如果創建虛擬環境失敗

**常見問題及解決方案：**

1. **權限錯誤**
   - 以管理員身份運行 PowerShell 或命令提示符
   - 或者在項目目錄上右鍵 → 屬性 → 安全 → 編輯權限

2. **執行策略錯誤（PowerShell）**
   ```powershell
   # 如果遇到 "無法載入腳本" 錯誤，執行：
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **路徑包含空格或特殊字符（重要！）**
   
   如果遇到錯誤：`Unable to copy ... venvlauncher.exe`，通常是路徑包含空格導致的。
   
   **解決步驟**：
   
   ```powershell
   # 步驟 1：先清理可能存在的部分創建的 venv 目錄
   if (Test-Path venv) {
       Remove-Item -Recurse -Force venv
   }
   
   # 步驟 2：使用引號創建虛擬環境
   python -m venv "venv"
   ```
   
   **如果仍然失敗**：
   
   ```powershell
   # 方法 A：使用完整路徑
   python -m venv "$PWD\venv"
   
   # 方法 B：以管理員身份運行 PowerShell 再執行
   # （右鍵點擊 PowerShell → 以系統管理員身分執行）
   python -m venv "venv"
   ```
   
   **最佳解決方案（推薦）**：
   - 將項目移動到沒有空格的路徑，例如：
     - `D:\2025_coding_project\20_climbing_score_counting_system`
     - `D:\coding\20_climbing_score_counting_system`
   - 這樣可以避免未來可能遇到的各種路徑相關問題

4. **防病毒軟件攔截**
   - 暫時關閉防病毒軟件
   - 或將項目目錄添加到防病毒軟件白名單

5. **Python 版本問題**
   ```powershell
   # 確認 Python 版本（需要 3.8+）
   python --version
   
   # 如果沒有 python，嘗試：
   py -3 -m venv venv
   ```

6. **手動清理後重試**
   ```powershell
   # 如果之前創建失敗，先刪除舊的 venv 目錄
   Remove-Item -Recurse -Force venv
   # 然後重新創建
   python -m venv venv
   ```

### 2. 安裝 Python 依賴

激活虛擬環境後，安裝項目依賴：

```bash
pip install -r requirements.txt
```

#### 如果遇到 "failed-wheel-build-for-install" 錯誤

這通常是因為 `mysqlclient` 在 Windows 上需要編譯，但缺少 MySQL 客戶端庫。我們已經使用 `pymysql` 作為替代方案：

**解決方案（已自動配置）**：
- `requirements.txt` 中使用 `pymysql` 替代 `mysqlclient`
- `climbing_system/__init__.py` 已配置自動使用 pymysql

**如果仍遇到問題**：

1. **升級 pip 和構建工具**：
   ```powershell
   python -m pip install --upgrade pip wheel setuptools
   ```

2. **單獨安裝每個包**：
   ```powershell
   pip install Django==4.2.7
   pip install pymysql==1.1.0
   pip install djangorestframework==3.14.0
   pip install django-cors-headers==4.3.1
   ```

3. **使用預編譯的 mysqlclient（進階）**：
   如果您確實需要 mysqlclient，可以：
   - 下載預編譯的 wheel：https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient
   - 或安裝 Visual Studio Build Tools 和 MySQL Connector/C

**注意**: 如果沒有使用虛擬環境，請確保您有權限安裝包，或者使用 `--user` 參數：
```bash
pip install --user -r requirements.txt
```

#### 如果遇到 Pillow 安裝失敗

**Pillow 是圖片處理庫，用於照片上傳功能。在 Windows 上安裝時可能遇到編譯錯誤。**

**解決方案（按順序嘗試）**：

1. **使用預編譯的 wheel 文件（推薦）**：
   ```powershell
   # 先升級 pip
   python -m pip install --upgrade pip
   
   # 使用 --only-binary 強制使用預編譯版本
   pip install --only-binary :all: Pillow
   ```

2. **如果方法 1 失敗，嘗試不指定版本**：
   ```powershell
   # 不指定版本，讓 pip 自動選擇兼容的預編譯版本
   pip install Pillow
   ```

3. **如果仍然失敗，可以暫時跳過照片上傳功能**：
   ```powershell
   # 先安裝其他依賴
   pip install Django==4.2.7
   pip install pymysql==1.1.0
   pip install djangorestframework==3.14.0
   pip install django-cors-headers==4.3.1
   
   # 照片上傳功能需要 Pillow，如果無法安裝可以暫時不使用該功能
   # 系統仍可正常運行，只是無法上傳照片
   ```

4. **安裝 Visual Studio Build Tools（進階，適用於需要從源代碼編譯的情況）**：
   - 下載並安裝 Visual Studio Build Tools：https://visualstudio.microsoft.com/downloads/
   - 選擇 "C++ build tools" 工作負載
   - 然後重新運行 `pip install Pillow`

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

#### 如果遇到 "Can't connect to MySQL server" 錯誤

**解決方案**：使用預設的 SQLite 配置（無需修改任何配置）

當前 `settings.py` 已配置為 SQLite，如果遇到連接錯誤，說明代碼中仍在使用 MySQL 配置。現在已修復為默認使用 SQLite。

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

# 初始化默認數據
python manage.py init_default_data

# 啟動服務器
python manage.py runserver
```

### 5. 訪問系統

啟動成功後，系統會自動創建：
- **房間**: 竹北岩館挑戰賽 (ID: 1)
- **成員**: 王小明、李大華（常態組）、張三（客製化組）

**訪問地址**：

- **排行榜頁面**: http://127.0.0.1:8000/api/leaderboard/1/
  - 🎯 **這是主要使用頁面**，可以直接開始添加路線和成績
  
- **管理後台**: http://127.0.0.1:8000/admin/
  - 首次使用需要創建超級用戶：`python manage.py createsuperuser`
  
- **API 文檔**: http://127.0.0.1:8000/api/

### 6. 手動創建數據（可選）

如果需要手動創建或重置數據：

```bash
# 使用初始化命令（如果數據已存在，不會重複創建）
python manage.py init_default_data

# 強制重新創建（會刪除現有數據）
python manage.py init_default_data --force
```

或在 Django shell 中：

```bash
python manage.py shell
```

```python
from scoring.models import Room, Member

# 創建房間
room = Room.objects.create(name="竹北岩館挑戰賽", standard_line_score=12)

# 創建成員（常態組）
Member.objects.create(room=room, name="王小明", is_custom_calc=False)
Member.objects.create(room=room, name="李大華", is_custom_calc=False)

# 創建成員（客製化組）
Member.objects.create(room=room, name="張三", is_custom_calc=True)

# 查看房間 ID
print(f"房間 ID: {room.id}")
```

## 常見問題

### MySQL 連接錯誤

如果遇到 `mysqlclient` 安裝問題：

**Windows 用戶**：
1. 下載 MySQL Connector/C：https://dev.mysql.com/downloads/connector/c/
2. 或使用 `pip install mysqlclient --only-binary :all:`

**替代方案**：使用 `pymysql`

```bash
pip install pymysql
```

在 `climbing_system/__init__.py` 中添加：

```python
import pymysql
pymysql.install_as_MySQLdb()
```

### 靜態文件未加載

運行：

```bash
python manage.py collectstatic --noinput
```

### 測試計分邏輯

運行測試套件：

```bash
python manage.py test scoring.tests
```

## 下一步

1. 通過管理後台創建房間和成員
2. 使用前端界面或 API 添加路線和成績
3. 查看即時更新的排行榜

