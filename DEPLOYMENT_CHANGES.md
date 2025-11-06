# AWS EC2 部署修改總結

本文檔總結了為 AWS EC2 部署所做的所有修改。

## 修改的文件

### 1. `requirements.txt`
- ✅ 添加了 `gunicorn>=21.2.0` 用於生產環境 WSGI 服務器

### 2. `climbing_system/settings.py`
- ✅ 修改 `SECRET_KEY` 支持從環境變數讀取
- ✅ 修改 `DEBUG` 支持從環境變數讀取（預設為 True，生產環境需設為 False）
- ✅ 修改 `ALLOWED_HOSTS` 支持從環境變數讀取
- ✅ 添加 `STATIC_ROOT` 用於收集靜態文件
- ✅ 修改 CORS 設置支持環境變數配置
- ✅ 增強日誌配置，生產環境寫入文件
- ✅ 添加生產環境安全設置（SSL、Cookie 安全等）

## 新增的文件

### 配置文件

1. **`gunicorn_config.py`**
   - Gunicorn 配置文件
   - 包含 worker 數量、日誌、超時等設置
   - 位置：項目根目錄

2. **`nginx/climbing_system.conf`**
   - Nginx 反向代理配置
   - 配置靜態文件和媒體文件服務
   - 配置代理到 Gunicorn
   - 位置：`/etc/nginx/sites-available/climbing_system.conf`

3. **`systemd/climbing_system.service`**
   - Systemd 服務文件
   - 用於管理 Gunicorn 進程
   - 位置：`/etc/systemd/system/climbing_system.service`

### 部署腳本

4. **`deploy.sh`**
   - 自動化部署腳本
   - 包含依賴安裝、遷移、收集靜態文件等步驟
   - 使用方法：`bash deploy.sh`

5. **`setup_ec2.sh`**
   - EC2 初始設置腳本
   - 安裝系統依賴、創建目錄等
   - 使用方法：`bash setup_ec2.sh`

### 文檔

6. **`AWS_EC2_DEPLOYMENT.md`**
   - 完整的部署指南
   - 包含所有部署步驟和故障排除

7. **`env.example`**
   - 環境變數配置範例
   - 可複製為 `.env` 文件使用

## 部署架構

```
Internet
   ↓
AWS EC2 (Nginx:80/443)
   ↓
Gunicorn (127.0.0.1:8000)
   ↓
Django Application
   ↓
SQLite Database (db.sqlite3)
```

## 環境變數配置

在 EC2 上需要設置以下環境變數（在 systemd 服務文件中或使用 .env 文件）：

```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ec2-ip
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

## 部署步驟摘要

1. 在 EC2 上運行 `setup_ec2.sh` 進行初始設置
2. 上傳項目文件到 `/var/www/Climbing_score_counter`
3. 創建虛擬環境並安裝依賴
4. 配置環境變數
5. 運行數據庫遷移
6. 收集靜態文件
7. 配置並啟動 Gunicorn 服務
8. 配置並啟動 Nginx
9. 測試部署

詳細步驟請參考 `AWS_EC2_DEPLOYMENT.md`。

## 注意事項

1. **SECRET_KEY**: 必須在生產環境中更改，使用強隨機密鑰
2. **DEBUG**: 生產環境必須設為 `False`
3. **ALLOWED_HOSTS**: 必須設置為實際的域名或 IP
4. **文件權限**: 確保 `www-data` 用戶有適當的權限
5. **日誌目錄**: 確保 `logs/` 目錄存在且有寫入權限
6. **媒體文件**: 確保 `media/` 目錄有寫入權限

## 服務管理命令

```bash
# Gunicorn 服務
sudo systemctl start climbing_system
sudo systemctl stop climbing_system
sudo systemctl restart climbing_system
sudo systemctl status climbing_system

# Nginx 服務
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl reload nginx
sudo systemctl status nginx
```

## 日誌位置

- Gunicorn 訪問日誌：`/var/www/Climbing_score_counter/logs/gunicorn_access.log`
- Gunicorn 錯誤日誌：`/var/www/Climbing_score_counter/logs/gunicorn_error.log`
- Django 日誌：`/var/www/Climbing_score_counter/logs/django.log`
- Nginx 訪問日誌：`/var/log/nginx/climbing_system_access.log`
- Nginx 錯誤日誌：`/var/log/nginx/climbing_system_error.log`
- Systemd 日誌：`sudo journalctl -u climbing_system -f`

## 後續優化建議

1. **SSL/HTTPS**: 使用 Let's Encrypt 配置 HTTPS
2. **備份策略**: 設置自動備份 SQLite 數據庫和媒體文件
3. **監控**: 設置日誌監控和錯誤告警
4. **性能優化**: 根據實際負載調整 Gunicorn workers 數量
5. **數據庫遷移**: 如果數據量大，考慮遷移到 PostgreSQL

