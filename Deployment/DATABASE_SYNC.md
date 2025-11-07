# 數據庫同步指南

本指南說明如何在本地開發環境和 AWS EC2 部署環境之間同步 SQLite 數據庫。

## 問題背景

在開發過程中，經常會遇到以下情況：
- 在部署環境（AWS EC2）上進行了許多操作（創建房間、添加成員、記錄成績等）
- 更新程序代碼時，`git pull` 可能會覆蓋本地的 `db.sqlite3`
- 導致部署環境的數據丟失

## 解決方案

我們提供了兩個腳本來解決這個問題：
1. **從服務器同步到本地** (`sync_database_from_server.sh`) - 下載部署環境的數據庫
2. **從本地同步到服務器** (`sync_database_to_server.sh`) - 上傳本地數據庫到部署環境

## 前置需求

1. SSH 訪問權限（已配置 SSH 密鑰）
2. 知道 EC2 實例的 IP 地址或域名
3. 本地已安裝 `sqlite3`（可選，用於查看數據庫信息）

## 使用方法

### 方法 1: 使用環境變數（推薦）

```bash
# 設置環境變數
export EC2_HOST=3.26.6.19  # 替換為您的 EC2 IP
export EC2_KEY=~/.ssh/your-key.pem  # 替換為您的 SSH 密鑰路徑
export EC2_USER=ubuntu  # 默認為 ubuntu

# 從服務器同步到本地
bash Deployment/sync_database_from_server.sh

# 從本地同步到服務器（會覆蓋服務器數據庫！）
bash Deployment/sync_database_to_server.sh
```

### 方法 2: 直接修改腳本

編輯 `Deployment/sync_database_from_server.sh` 和 `Deployment/sync_database_to_server.sh`，修改以下變數：

```bash
EC2_USER="ubuntu"
EC2_HOST="3.26.6.19"  # 您的 EC2 IP
EC2_KEY="~/.ssh/your-key.pem"  # 您的 SSH 密鑰路徑
```

## 詳細說明

### 1. 從服務器同步到本地

**使用場景**：
- 部署環境有最新的數據，需要同步到本地進行測試
- 更新代碼前，先備份部署環境的數據庫

**執行步驟**：

```bash
bash Deployment/sync_database_from_server.sh
```

**腳本會自動執行**：
1. 檢查 SSH 連接
2. 檢查遠程數據庫是否存在
3. 備份本地數據庫（如果存在）到 `backups/` 目錄
4. 下載遠程數據庫到本地
5. 顯示數據庫基本信息

**示例輸出**：

```
==========================================
從 AWS EC2 同步數據庫到本地
==========================================
檢查 SSH 連接...
檢查遠程數據庫...
備份本地數據庫到: backups/db_local_backup_20251107_171500.sqlite3
✅ 本地數據庫已備份
下載遠程數據庫...
db.sqlite3                                   100%  512KB   512.0KB/s   00:00
✅ 數據庫下載成功！
   文件大小: 512K
   位置: db.sqlite3

數據庫信息:
   表數量: 8

==========================================
同步完成！
==========================================
```

### 2. 從本地同步到服務器

**使用場景**：
- 本地開發環境有測試數據，需要同步到部署環境
- 修復部署環境的數據問題

**⚠️  警告**：此操作會覆蓋服務器上的數據庫！

**執行步驟**：

```bash
bash Deployment/sync_database_to_server.sh
```

**腳本會自動執行**：
1. 檢查本地數據庫是否存在
2. 要求確認操作（輸入 `yes` 繼續）
3. 檢查 SSH 連接
4. 在服務器上備份現有數據庫到 `backups/` 目錄
5. 上傳本地數據庫到服務器
6. 設置服務器文件權限
7. 可選：重啟 Gunicorn 服務

**示例輸出**：

```
==========================================
將本地數據庫同步到 AWS EC2 服務器
==========================================
⚠️  警告：此操作會覆蓋服務器上的數據庫！
   服務器: ubuntu@3.26.6.19
   目標文件: /var/www/Climbing_score_counter/db.sqlite3

確定要繼續嗎？(yes/no): yes
檢查 SSH 連接...
在服務器上備份現有數據庫...
✅ 服務器數據庫已備份到: /var/www/Climbing_score_counter/backups/db_backup_before_sync_20251107_171500.sqlite3
上傳本地數據庫到服務器...
db.sqlite3                                   100%  512KB   512.0KB/s   00:00
設置服務器文件權限...
✅ 文件權限已設置

是否重啟 Gunicorn 服務以應用更改？(yes/no): yes
重啟 Gunicorn 服務...
✅ 服務已重啟

==========================================
同步完成！
==========================================
```

## 最佳實踐

### 1. 更新代碼前同步數據庫

```bash
# 1. 先從服務器同步數據庫到本地（備份部署環境的數據）
bash Deployment/sync_database_from_server.sh

# 2. 更新代碼
git pull origin main

# 3. 如果需要，可以將本地數據庫同步回服務器
# bash Deployment/sync_database_to_server.sh
```

### 2. 定期備份

建議定期從服務器同步數據庫到本地作為備份：

```bash
# 每週執行一次
bash Deployment/sync_database_from_server.sh
```

### 3. 使用 Git 忽略數據庫

確保 `db.sqlite3` 在 `.gitignore` 中（已配置），避免意外提交：

```gitignore
db.sqlite3
*.sqlite3
*.sqlite
```

### 4. 部署腳本自動備份

`deploy.sh` 腳本已經包含自動備份功能，在 `git pull` 前會自動備份本地數據庫。

## 故障排除

### 問題 1: SSH 連接失敗

**錯誤信息**：
```
❌ 無法連接到服務器 ubuntu@3.26.6.19
```

**解決方法**：
1. 檢查 EC2_HOST 是否正確
2. 檢查 EC2_KEY 路徑是否正確
3. 檢查 SSH 密鑰權限：`chmod 600 ~/.ssh/your-key.pem`
4. 檢查安全組是否允許 SSH 連接（端口 22）

### 問題 2: 權限錯誤

**錯誤信息**：
```
Permission denied (publickey)
```

**解決方法**：
1. 確認 SSH 密鑰已添加到 EC2 實例
2. 檢查密鑰文件權限：`chmod 600 ~/.ssh/your-key.pem`
3. 確認使用正確的用戶名（通常是 `ubuntu`）

### 問題 3: 數據庫文件不存在

**錯誤信息**：
```
❌ 遠程數據庫不存在: /var/www/Climbing_score_counter/db.sqlite3
```

**解決方法**：
1. 確認項目目錄路徑正確
2. 在服務器上檢查數據庫位置：`ls -la /var/www/Climbing_score_counter/db.sqlite3`
3. 如果數據庫在其他位置，修改腳本中的 `PROJECT_DIR` 變數

### 問題 4: 文件權限問題

**錯誤信息**：
```
chown: changing ownership: Operation not permitted
```

**解決方法**：
1. 確認腳本在服務器上有 sudo 權限
2. 手動設置權限：`sudo chown www-data:www-data /var/www/Climbing_score_counter/db.sqlite3`

## 自動化腳本

### Windows (PowerShell)

創建 `sync_db_from_server.ps1`：

```powershell
$env:EC2_HOST = "3.26.6.19"
$env:EC2_KEY = "$env:USERPROFILE\.ssh\your-key.pem"
$env:EC2_USER = "ubuntu"

bash Deployment/sync_database_from_server.sh
```

### macOS/Linux

創建 `sync_db_from_server.sh`：

```bash
#!/bin/bash
export EC2_HOST="3.26.6.19"
export EC2_KEY="$HOME/.ssh/your-key.pem"
export EC2_USER="ubuntu"

bash Deployment/sync_database_from_server.sh
```

## 相關文檔

- `Deployment/AWS_EC2_DEPLOYMENT.md` - 部署指南
- `Deployment/deploy.sh` - 自動部署腳本
- `Deployment/DEPLOYMENT_CHANGES.md` - 部署變更說明

