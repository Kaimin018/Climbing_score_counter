# 數據庫設置指南

## 當前配置

系統已預設使用 **SQLite** 數據庫，無需額外設置即可運行。

## 兩種數據庫選項

### 選項 1：SQLite（預設，推薦用於開發和測試）

**優點**：
- ✅ 無需安裝和配置
- ✅ 無需啟動服務
- ✅ 適合開發和測試
- ✅ 數據存儲在單個文件 `db.sqlite3` 中

**缺點**：
- ⚠️ 不適合高併發生產環境
- ⚠️ 功能較 MySQL 少

**使用方式**：
默認配置已啟用 SQLite，直接運行即可：

```bash
python manage.py migrate
python manage.py runserver
```

### 選項 2：MySQL（推薦用於生產環境）

**優點**：
- ✅ 性能更好，適合生產環境
- ✅ 支持更高併發
- ✅ 功能更豐富

**缺點**：
- ⚠️ 需要安裝和啟動 MySQL 服務
- ⚠️ 需要創建數據庫和配置

## 如何切換到 MySQL

### 步驟 1：啟動 MySQL 服務

#### Windows 用戶

1. **檢查 MySQL 是否已安裝**：
   ```powershell
   Get-Service -Name "*mysql*"
   ```

2. **如果已安裝但未啟動**：
   ```powershell
   # 啟動 MySQL 服務
   Start-Service -Name "MySQL80"  # 根據您的服務名稱調整
   ```

3. **如果未安裝 MySQL**：
   - 下載並安裝 MySQL：https://dev.mysql.com/downloads/mysql/
   - 或使用 XAMPP：https://www.apachefriends.org/
   - 安裝後啟動 MySQL 服務

### 步驟 2：創建數據庫

使用 MySQL 命令行或 phpMyAdmin 創建數據庫：

```sql
CREATE DATABASE climbing_score_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 步驟 3：修改 Django 設置

編輯 `climbing_system/settings.py`：

1. **註釋掉 SQLite 配置**：
   ```python
   # DATABASES = {
   #     'default': {
   #         'ENGINE': 'django.db.backends.sqlite3',
   #         'NAME': BASE_DIR / 'db.sqlite3',
   #     }
   # }
   ```

2. **取消註釋 MySQL 配置**：
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'climbing_score_db',
           'USER': 'root',
           'PASSWORD': 'your_password',  # 填入您的 MySQL 密碼
           'HOST': 'localhost',
           'PORT': '3306',
           'OPTIONS': {
               'charset': 'utf8mb4',
           },
       }
   }
   ```

### 步驟 4：運行遷移

```bash
python manage.py migrate
```

## 常見問題

### Q: 如何檢查 MySQL 是否運行？

**Windows PowerShell**：
```powershell
Get-Service -Name "*mysql*"
```

**或使用 MySQL 客戶端**：
```bash
mysql -u root -p
```

### Q: 遇到 "Can't connect to MySQL server" 錯誤？

1. **確認 MySQL 服務正在運行**：
   ```powershell
   Get-Service -Name "*mysql*"
   Start-Service -Name "MySQL80"  # 如果未運行
   ```

2. **檢查端口是否正確**：
   默認 MySQL 端口為 3306，確認沒有被其他程序占用

3. **檢查用戶名和密碼**：
   確認 `settings.py` 中的用戶名和密碼正確

4. **暫時使用 SQLite**：
   如果只是想快速測試，可以繼續使用 SQLite（當前預設配置）

### Q: SQLite 和 MySQL 之間如何遷移數據？

**從 SQLite 遷移到 MySQL**：

1. 導出 SQLite 數據：
   ```bash
   python manage.py dumpdata > data.json
   ```

2. 切換到 MySQL 配置

3. 運行遷移：
   ```bash
   python manage.py migrate
   ```

4. 導入數據：
   ```bash
   python manage.py loaddata data.json
   ```

**注意**：在切換數據庫時，需要重新運行 `python manage.py migrate`

## 當前狀態

✅ **SQLite 已配置並可以正常使用**

系統現在使用 SQLite 數據庫，所有功能都可以正常運行。如果您需要使用 MySQL，請按照上述步驟進行切換。








