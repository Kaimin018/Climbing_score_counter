# AWS EC2 部署指南

本指南說明如何將攀岩計分系統部署到 AWS EC2，使用 SQLite 數據庫、Nginx 反向代理和 Gunicorn WSGI 服務器。

## 架構概覽

```
Internet
   ↓
AWS EC2 (Nginx:80)
   ↓
Gunicorn (127.0.0.1:8000)
   ↓
Django Application
   ↓
SQLite Database
```

## 前置需求

1. AWS EC2 實例（建議使用 Ubuntu 22.04 LTS）
2. 域名（可選，也可以使用 IP 地址）
3. SSH 訪問權限

## 步驟 1: 準備 EC2 實例

### 1.1 啟動 EC2 實例

1. 登入 AWS Console
2. 啟動新的 EC2 實例
3. 選擇 Ubuntu 22.04 LTS AMI
4. 建議最小配置：
   - Instance Type: t3.micro 或 t3.small
   - Storage: 20GB 或更多（用於存儲媒體文件）
5. 配置安全組：
   - 開放端口 22 (SSH)
   - 開放端口 80 (HTTP)
   - 開放端口 443 (HTTPS，如果使用 SSL)

### 1.2 連接到 EC2 實例

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

## 步驟 2: 安裝系統依賴

```bash
# 更新系統
sudo apt update
sudo apt upgrade -y

# 安裝 Python 和必要工具
sudo apt install -y python3 python3-pip python3-venv nginx

# 安裝其他必要工具
sudo apt install -y git curl
```

## 步驟 3: 設置項目目錄

```bash
# 創建項目目錄
sudo mkdir -p /var/www/Climbing_score_counter
sudo chown -R $USER:$USER /var/www/Climbing_score_counter

# 進入目錄
cd /var/www/Climbing_score_counter
```

## 步驟 4: 上傳項目文件

### 方法 1: 使用 Git（推薦）

```bash
# 克隆項目（如果使用 Git）
git clone https://github.com/your-username/climbing_score_counting_system.git .

# 或使用 scp 上傳文件
# 在本地執行：
# scp -r -i your-key.pem /path/to/project/* ubuntu@your-ec2-ip:/var/www/Climbing_score_counter/
```

### 方法 2: 使用 SCP

在本地電腦執行：

```bash
scp -r -i your-key.pem \
    climbing_system/ \
    scoring/ \
    templates/ \
    static/ \
    manage.py \
    requirements.txt \
    gunicorn_config.py \
    ubuntu@your-ec2-ip:/var/www/Climbing_score_counter/
```

## 步驟 5: 設置 Python 虛擬環境

```bash
cd /var/www/Climbing_score_counter

# 創建虛擬環境
python3 -m venv venv

# 激活虛擬環境
source venv/bin/activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt
```

## 步驟 6: 配置 Django 設置

### 6.1 生成新的 SECRET_KEY

```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6.2 創建環境變數文件（可選）

創建 `/var/www/Climbing_score_counter/.env`：

```bash
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ec2-ip
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

或者直接在 systemd 服務文件中設置環境變數（見步驟 8）。

## 步驟 7: 初始化數據庫

```bash
# 確保在虛擬環境中
source venv/bin/activate

# 運行遷移
python manage.py migrate

# 創建超級用戶（可選）
python manage.py createsuperuser
```

## 步驟 8: 收集靜態文件

```bash
# 創建靜態文件目錄
mkdir -p staticfiles

# 收集靜態文件
python manage.py collectstatic --noinput
```

## 步驟 9: 配置 Gunicorn

### 9.1 複製 Gunicorn 配置文件

```bash
# 確保 gunicorn_config.py 在項目根目錄
# 檢查配置文件路徑
ls -la gunicorn_config.py
```

### 9.2 測試 Gunicorn

```bash
# 激活虛擬環境
source venv/bin/activate

# 設置環境變數
export SECRET_KEY="your-secret-key"
export DEBUG="False"
export ALLOWED_HOSTS="your-domain.com,your-ec2-ip"

# 測試運行 Gunicorn
gunicorn --config gunicorn_config.py climbing_system.wsgi:application
```

如果成功，應該能看到 Gunicorn 啟動訊息。按 Ctrl+C 停止。

## 步驟 10: 配置 Systemd 服務

### 10.1 複製服務文件

```bash
# 複製 systemd 服務文件
sudo cp systemd/climbing_system.service /etc/systemd/system/

# 編輯服務文件，設置正確的路徑和環境變數
sudo nano /etc/systemd/system/climbing_system.service
```

### 10.2 修改服務文件

確保以下設置正確：

- `WorkingDirectory`: `/var/www/Climbing_score_counter`
- `User` 和 `Group`: `www-data`（或您的用戶）
- `Environment`: 設置所有必要的環境變數
- `ExecStart`: Gunicorn 命令路徑正確

### 10.3 啟動服務

```bash
# 重新加載 systemd
sudo systemctl daemon-reload

# 啟用服務（開機自動啟動）
sudo systemctl enable climbing_system

# 啟動服務
sudo systemctl start climbing_system

# 檢查狀態
sudo systemctl status climbing_system
```

### 10.4 查看日誌

```bash
# 查看服務日誌
sudo journalctl -u climbing_system -f

# 查看應用日誌
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
```

## 步驟 11: 配置 Nginx

### 11.1 複製 Nginx 配置文件

```bash
# 複製配置文件
sudo cp nginx/climbing_system.conf /etc/nginx/sites-available/

# 創建符號連結
sudo ln -s /etc/nginx/sites-available/climbing_system.conf /etc/nginx/sites-enabled/

# 刪除默認配置（可選）
sudo rm /etc/nginx/sites-enabled/default
```

### 11.2 編輯 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/climbing_system.conf
```

修改以下內容：

- `server_name`: 替換為您的域名或 IP 地址
- 確保所有路徑正確

### 11.3 測試和重載 Nginx

```bash
# 測試配置
sudo nginx -t

# 如果測試通過，重載 Nginx
sudo systemctl reload nginx

# 或重啟 Nginx
sudo systemctl restart nginx

# 檢查狀態
sudo systemctl status nginx
```

## 步驟 12: 設置文件權限

```bash
# 設置項目目錄權限
sudo chown -R www-data:www-data /var/www/Climbing_score_counter
sudo chmod -R 755 /var/www/Climbing_score_counter

# 設置媒體和日誌目錄權限（需要寫入權限）
sudo chmod -R 775 /var/www/Climbing_score_counter/media
sudo chmod -R 775 /var/www/Climbing_score_counter/logs
sudo chmod -R 775 /var/www/Climbing_score_counter/staticfiles
```

## 步驟 13: 創建日誌目錄

```bash
mkdir -p /var/www/Climbing_score_counter/logs
sudo chown -R www-data:www-data /var/www/Climbing_score_counter/logs
```

## 步驟 14: 測試部署

1. 在瀏覽器中訪問 `http://your-ec2-ip` 或 `http://your-domain.com`
2. 檢查是否能看到首頁
3. 測試創建房間、上傳圖片等功能

## 步驟 15: 配置 SSL（可選但強烈推薦）

### 使用 Let's Encrypt

```bash
# 安裝 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 獲取 SSL 證書
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自動續期測試
sudo certbot renew --dry-run
```

## 日常維護

### 更新代碼

```bash
cd /var/www/Climbing_score_counter
source venv/bin/activate

# 拉取最新代碼（如果使用 Git）
git pull

# 或使用部署腳本
bash deploy.sh
```

### 查看日誌

```bash
# Gunicorn 日誌
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
tail -f /var/www/Climbing_score_counter/logs/gunicorn_access.log

# Django 日誌
tail -f /var/www/Climbing_score_counter/logs/django.log

# Nginx 日誌
sudo tail -f /var/log/nginx/climbing_system_error.log
sudo tail -f /var/log/nginx/climbing_system_access.log

# Systemd 服務日誌
sudo journalctl -u climbing_system -f
```

### 重啟服務

```bash
# 重啟 Gunicorn
sudo systemctl restart climbing_system

# 重啟 Nginx
sudo systemctl restart nginx

# 重載配置（不中斷服務）
sudo systemctl reload nginx
```

### 備份數據庫

```bash
# 備份 SQLite 數據庫
cp /var/www/Climbing_score_counter/db.sqlite3 \
   /var/www/Climbing_score_counter/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# 備份媒體文件
tar -czf /var/www/Climbing_score_counter/backups/media_$(date +%Y%m%d_%H%M%S).tar.gz \
    /var/www/Climbing_score_counter/media/
```

## 故障排除

### Gunicorn 無法啟動

1. 檢查服務狀態：`sudo systemctl status climbing_system`
2. 查看日誌：`sudo journalctl -u climbing_system -n 50`
3. 檢查配置文件路徑和權限
4. 確認環境變數設置正確

### Nginx 502 Bad Gateway

1. 檢查 Gunicorn 是否運行：`sudo systemctl status climbing_system`
2. 檢查端口 8000 是否被監聽：`sudo netstat -tlnp | grep 8000`
3. 查看 Nginx 錯誤日誌：`sudo tail -f /var/log/nginx/climbing_system_error.log`

### 靜態文件無法加載

1. 確認已運行 `collectstatic`
2. 檢查 `STATIC_ROOT` 目錄是否存在且有正確權限
3. 檢查 Nginx 配置中的 `alias` 路徑是否正確

### 媒體文件無法上傳

1. 檢查 `media` 目錄權限：`ls -la /var/www/Climbing_score_counter/media`
2. 確認目錄有寫入權限：`sudo chmod -R 775 /var/www/Climbing_score_counter/media`
3. 檢查磁盤空間：`df -h`

## 安全建議

1. **更改 SECRET_KEY**: 使用強隨機密鑰
2. **設置 DEBUG=False**: 生產環境必須關閉調試模式
3. **配置 ALLOWED_HOSTS**: 只允許您的域名
4. **使用 HTTPS**: 配置 SSL 證書
5. **定期更新**: 保持系統和依賴包更新
6. **防火牆**: 只開放必要端口
7. **備份**: 定期備份數據庫和媒體文件

## 性能優化

1. **增加 Gunicorn Workers**: 根據 CPU 核心數調整
2. **啟用 Nginx 緩存**: 對靜態文件啟用緩存
3. **使用 CDN**: 將靜態文件放到 CDN（可選）
4. **數據庫優化**: 如果數據量大，考慮遷移到 PostgreSQL

## 聯繫與支持

如有問題，請查看：
- 項目文檔：`ARCHITECTURE.md`
- Django 日誌：`logs/django.log`
- Gunicorn 日誌：`logs/gunicorn_error.log`

