# AWS EC2 部署快速參考

## 快速部署步驟

### 1. 在 EC2 上初始設置
```bash
bash setup_ec2.sh
```

### 2. 上傳項目文件
```bash
# 使用 scp 或 git clone
scp -r -i your-key.pem * ubuntu@your-ec2-ip:/var/www/Climbing_score_counter/
```

### 3. 設置虛擬環境和依賴
```bash
cd /var/www/Climbing_score_counter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 生成 SECRET_KEY
```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. 配置環境變數（編輯 systemd 服務文件）
```bash
sudo nano /etc/systemd/system/climbing_system.service
# 設置 SECRET_KEY, DEBUG=False, ALLOWED_HOSTS 等
```

### 6. 初始化數據庫
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 7. 配置並啟動服務
```bash
# 複製配置文件
sudo cp nginx/climbing_system.conf /etc/nginx/sites-available/
sudo cp systemd/climbing_system.service /etc/systemd/system/

# 編輯配置文件（設置域名、路徑等）
sudo nano /etc/nginx/sites-available/climbing_system.conf
sudo nano /etc/systemd/system/climbing_system.service

# 啟用 Nginx 配置
sudo ln -s /etc/nginx/sites-available/climbing_system.conf /etc/nginx/sites-enabled/

# 啟動服務
sudo systemctl daemon-reload
sudo systemctl enable climbing_system
sudo systemctl start climbing_system
sudo systemctl restart nginx
```

### 8. 設置權限
```bash
sudo chown -R www-data:www-data /var/www/Climbing_score_counter
sudo chmod -R 755 /var/www/Climbing_score_counter
sudo chmod -R 775 /var/www/Climbing_score_counter/media
sudo chmod -R 775 /var/www/Climbing_score_counter/logs
```

## 常用命令

### 服務管理
```bash
# Gunicorn
sudo systemctl status climbing_system
sudo systemctl restart climbing_system
sudo systemctl stop climbing_system
sudo systemctl start climbing_system

# Nginx
sudo systemctl status nginx
sudo systemctl restart nginx
sudo nginx -t  # 測試配置
```

### 查看日誌
```bash
# Gunicorn
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
tail -f /var/www/Climbing_score_counter/logs/gunicorn_access.log

# Django
tail -f /var/www/Climbing_score_counter/logs/django.log

# Nginx
sudo tail -f /var/log/nginx/climbing_system_error.log
sudo tail -f /var/log/nginx/climbing_system_access.log

# Systemd
sudo journalctl -u climbing_system -f
```

### 更新代碼
```bash
cd /var/www/Climbing_score_counter
source venv/bin/activate
# 拉取最新代碼或上傳新文件
bash deploy.sh
```

## 環境變數清單

必須設置的環境變數（在 systemd 服務文件中）：

```bash
SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-ec2-ip
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

## 文件路徑

- 項目目錄：`/var/www/Climbing_score_counter`
- 靜態文件：`/var/www/Climbing_score_counter/staticfiles/`
- 媒體文件：`/var/www/Climbing_score_counter/media/`
- 日誌目錄：`/var/www/Climbing_score_counter/logs/`
- Nginx 配置：`/etc/nginx/sites-available/climbing_system.conf`
- Systemd 服務：`/etc/systemd/system/climbing_system.service`

## 故障排除

### 502 Bad Gateway
```bash
# 檢查 Gunicorn 是否運行
sudo systemctl status climbing_system

# 檢查端口
sudo netstat -tlnp | grep 8000

# 查看錯誤日誌
tail -f /var/www/Climbing_score_counter/logs/gunicorn_error.log
```

### 靜態文件無法加載
```bash
# 重新收集靜態文件
python manage.py collectstatic --noinput

# 檢查權限
ls -la /var/www/Climbing_score_counter/staticfiles/
```

### 媒體文件無法上傳
```bash
# 檢查權限
sudo chmod -R 775 /var/www/Climbing_score_counter/media
sudo chown -R www-data:www-data /var/www/Climbing_score_counter/media
```

## 安全檢查清單

- [ ] SECRET_KEY 已更改
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS 已設置
- [ ] CORS 已正確配置
- [ ] 文件權限已設置
- [ ] SSL/HTTPS 已配置（推薦）

## 詳細文檔

- 完整部署指南：`AWS_EC2_DEPLOYMENT.md`
- 修改總結：`DEPLOYMENT_CHANGES.md`
- 環境變數範例：`env.example`

