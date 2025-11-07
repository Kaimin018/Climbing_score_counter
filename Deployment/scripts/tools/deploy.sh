#!/bin/bash
# AWS EC2 部署腳本
# 使用方法：bash Deployment/deploy.sh

set -e

# 配置
PROJECT_DIR="/var/www/Climbing_score_counter"
VENV_DIR="$PROJECT_DIR/venv"
SERVER_CONFIG="$PROJECT_DIR/.server-config"

# 應用服務器配置（自動替換占位符）
apply_server_config() {
    if [ ! -f "$SERVER_CONFIG" ]; then
        echo "⚠️  未找到服務器配置文件，跳過自動配置"
        return 0
    fi
    
    # 修復配置文件權限
    if [ ! -r "$SERVER_CONFIG" ]; then
        CURRENT_USER=$(whoami)
        sudo chown $CURRENT_USER:$CURRENT_USER "$SERVER_CONFIG" 2>/dev/null || true
        sudo chmod 600 "$SERVER_CONFIG" 2>/dev/null || true
    fi
    
    source "$SERVER_CONFIG"
    
    # 驗證配置變數
    if [ -z "$DOMAIN" ] || [ -z "$EC2_IP" ] || [ -z "$SECRET_KEY" ]; then
        echo "⚠️  配置文件缺少必要變數，跳過自動配置"
        return 0
    fi
    
    WWW_DOMAIN=${WWW_DOMAIN:-www.$DOMAIN}
    
    # 更新 Systemd 服務配置
    SYSTEMD_SERVICE="/etc/systemd/system/climbing_system.service"
    if [ ! -f "$SYSTEMD_SERVICE" ] && [ -f "$PROJECT_DIR/Deployment/systemd/climbing_system.service" ]; then
        sudo cp "$PROJECT_DIR/Deployment/systemd/climbing_system.service" "$SYSTEMD_SERVICE"
    fi
    
    if [ -f "$SYSTEMD_SERVICE" ]; then
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-secret-key-here|$SECRET_KEY|g" "$SYSTEMD_SERVICE"
        
        # 修復舊路徑
        if grep -q "/var/www/Climbing_score_counter/gunicorn_config.py" "$SYSTEMD_SERVICE"; then
            sudo sed -i "s|/var/www/Climbing_score_counter/gunicorn_config.py|/var/www/Climbing_score_counter/Deployment/gunicorn_config.py|g" "$SYSTEMD_SERVICE"
        fi
    fi
    
    # 更新 Nginx 配置
    NGINX_AVAILABLE="/etc/nginx/sites-available/climbing_system.conf"
    NGINX_ENABLED="/etc/nginx/sites-enabled/climbing_system.conf"
    
    if [ ! -f "$NGINX_AVAILABLE" ] && [ -f "$PROJECT_DIR/Deployment/nginx/climbing_system.conf" ]; then
        sudo cp "$PROJECT_DIR/Deployment/nginx/climbing_system.conf" "$NGINX_AVAILABLE"
        [ ! -L "$NGINX_ENABLED" ] && sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
    fi
    
    if [ -f "$NGINX_AVAILABLE" ]; then
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$NGINX_AVAILABLE"
    fi
}

# 檢查項目目錄
[ ! -d "$PROJECT_DIR" ] && { echo "錯誤: 項目目錄不存在"; exit 1; }
cd $PROJECT_DIR || { echo "錯誤: 無法進入項目目錄"; exit 1; }

# 應用服務器配置
apply_server_config

# Git 更新
if [ -d ".git" ]; then
    # 配置 Git 安全目錄
    if ! git config --global --get safe.directory | grep -q "$PROJECT_DIR"; then
        git config --global --add safe.directory "$PROJECT_DIR"
    fi
    
    # 修復 .git 目錄權限
    if [ ! -w ".git/FETCH_HEAD" ] 2>/dev/null; then
        CURRENT_USER=$(whoami)
        sudo chown -R $CURRENT_USER:$CURRENT_USER .git 2>/dev/null || true
    fi
    
    # 修復項目文件權限
    CURRENT_USER=$(whoami)
    if [ ! -w "." ] 2>/dev/null || [ ! -w "Deployment" ] 2>/dev/null; then
        if ! groups | grep -q www-data; then
            sudo usermod -a -G www-data $CURRENT_USER 2>/dev/null || true
        fi
        sudo chmod -R g+w "$PROJECT_DIR" 2>/dev/null || true
    fi
    
    git fetch origin
    
    # 處理數據庫文件衝突
    if git diff --quiet db.sqlite3 2>/dev/null; then
        git reset --hard origin/main || git reset --hard origin/master
    else
        if [ -f "db.sqlite3" ]; then
            mkdir -p backups
            cp db.sqlite3 backups/db_local_backup_$(date +%Y%m%d_%H%M%S).sqlite3 2>/dev/null || true
        fi
        git checkout -- db.sqlite3 2>/dev/null || true
        git reset --hard origin/main || git reset --hard origin/master
        echo "ℹ️  提示：從服務器同步數據庫: bash Deployment/sync_database_from_server.sh"
    fi
    
    # 重新應用配置（模板文件可能已更新）
    apply_server_config
fi

# 創建虛擬環境
if [ ! -d "$VENV_DIR" ]; then
    if [ ! -w "$PROJECT_DIR" ]; then
        CURRENT_USER=$(whoami)
        sudo chmod g+w "$PROJECT_DIR" 2>/dev/null || true
    fi
    python3 -m venv $VENV_DIR
fi

# 激活虛擬環境
source $VENV_DIR/bin/activate

# 安裝系統依賴（pyheif）
sudo apt-get update -qq
sudo apt-get install -y libheif-dev libde265-dev libjpeg-dev zlib1g-dev 2>/dev/null || true

# 安裝 Python 依賴
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 數據庫遷移
python manage.py makemigrations --noinput || true
if [ -f "db.sqlite3" ] && [ ! -w "db.sqlite3" ]; then
    sudo chmod 664 db.sqlite3 2>/dev/null || true
    sudo chown www-data:www-data db.sqlite3 2>/dev/null || true
fi
python manage.py migrate --noinput

# 創建必要目錄
sudo mkdir -p $PROJECT_DIR/{logs,media,staticfiles,backups}

# 收集靜態文件
CURRENT_USER=$(whoami)
if [ -d "$PROJECT_DIR/staticfiles" ]; then
    sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR/staticfiles 2>/dev/null || true
    sudo chmod -R 755 $PROJECT_DIR/staticfiles 2>/dev/null || true
fi
python manage.py collectstatic --noinput --clear

# 設置文件權限
sudo chown -R www-data:www-data $PROJECT_DIR/{logs,media,staticfiles,backups} 2>/dev/null || true
sudo chmod -R 775 $PROJECT_DIR/{logs,media,backups} 2>/dev/null || true
sudo chmod -R 755 $PROJECT_DIR/staticfiles 2>/dev/null || true

if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    sudo chown www-data:www-data "$PROJECT_DIR/db.sqlite3" 2>/dev/null || true
    sudo chmod 664 "$PROJECT_DIR/db.sqlite3" 2>/dev/null || true
fi

if [ -f "$SERVER_CONFIG" ]; then
    sudo chmod 600 "$SERVER_CONFIG" 2>/dev/null || true
fi

# 重啟服務
sudo systemctl daemon-reload
sudo systemctl enable climbing_system
sudo systemctl restart climbing_system
sudo nginx -t && sudo systemctl reload nginx

echo "✅ 部署完成"
