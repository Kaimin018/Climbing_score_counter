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
git pull origin main
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
