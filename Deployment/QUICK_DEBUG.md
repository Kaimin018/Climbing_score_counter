# 快速調試指南

本文件包含開發和調試時最常用的命令。

## 連接服務器

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@3.26.6.19
```

## 進入項目目錄

```bash
cd /var/www/Climbing_score_counter
```

## 更新代碼

```bash
# 正常更新
git pull origin main

# 如果遇到文件冲突（文件结构重构后），手动处理：
# 1. 备份数据库（重要！）
mkdir -p backups
cp db.sqlite3 backups/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3

# 2. 暂存所有修改
git stash

# 3. 强制重置到远程版本（使用新结构）
git fetch origin
git reset --hard origin/main

# 4. 恢复数据库
cp backups/db_backup_*.sqlite3 db.sqlite3
sudo chown www-data:www-data db.sqlite3
sudo chmod 664 db.sqlite3

# 注意：如果新脚本已推送，可以使用：
# bash Deployment/scripts/tools/fix_git_conflict.sh
```

## 部署更新

```bash
bash Deployment/deploy.sh
```

## 創建虛擬環境（首次設置）

```bash
python3 -m venv venv
```

## 激活虛擬環境

```bash
source venv/bin/activate
```

## 數據庫同步（重要）

### 從服務器同步到本地（更新代碼前執行）

**Windows 用戶（推薦）**：
```bash
# 方法1: 使用批處理文件（雙擊運行）
Deployment\sync_db_from_server.bat

# 方法2: 使用 Git Bash
export EC2_HOST=3.26.6.19
export EC2_KEY=~/.ssh/your-key.pem
bash Deployment/sync_database_from_server.sh
```

**macOS/Linux 用戶**：
```bash
export EC2_HOST=3.26.6.19
export EC2_KEY=~/.ssh/your-key.pem
bash Deployment/sync_database_from_server.sh
```

### 從本地同步到服務器（覆蓋服務器數據庫）

```bash
# 在本地執行
export EC2_HOST=3.26.6.19
export EC2_KEY=~/.ssh/your-key.pem
bash Deployment/sync_database_to_server.sh
```

## 查看服務狀態

```bash
sudo systemctl status climbing_system
sudo systemctl status nginx
```

## 查看日誌

```bash
# Gunicorn 日誌
sudo journalctl -u climbing_system -f

# Nginx 錯誤日誌
sudo tail -f /var/log/nginx/error.log

# Django 日誌
tail -f logs/django.log
```

## 重啟服務

```bash
sudo systemctl restart climbing_system
sudo systemctl restart nginx
```

## 檢查端口

```bash
sudo netstat -tlnp | grep -E ':(80|8000|443)'
```

## 測試 API

```bash
curl http://127.0.0.1:8000/api/rooms/
```

## 故障排除

### 502 Bad Gateway（快速修复）

**快速诊断和修复**：
```bash
# 方法1: 使用自动修复脚本（如果已推送）
bash Deployment/scripts/tools/fix_502_gateway.sh

# 方法2: 手动快速修复
# 1. 检查并启动 Gunicorn
sudo systemctl status climbing_system
sudo systemctl start climbing_system

# 2. 检查端口
sudo netstat -tlnp | grep 8000

# 3. 测试本地连接
curl http://127.0.0.1:8000/

# 4. 查看错误日志
sudo journalctl -u climbing_system -n 50
sudo tail -20 /var/log/nginx/error.log

# 5. 重启服务
sudo systemctl restart climbing_system
sudo systemctl reload nginx
```

**详细文档**：`docs/troubleshooting/FIX_502_BAD_GATEWAY.md`
