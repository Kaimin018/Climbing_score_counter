#!/bin/bash
# AWS EC2 部署腳本
# 使用方法：bash deploy.sh

set -e  # 遇到錯誤立即退出

echo "開始部署攀岩計分系統..."

# 項目目錄
PROJECT_DIR="/var/www/Climbing_score_counter"
VENV_DIR="$PROJECT_DIR/venv"
SERVER_CONFIG="$PROJECT_DIR/.server-config"

# 配置管理函數
apply_server_config() {
    if [ ! -f "$SERVER_CONFIG" ]; then
        echo "⚠️  警告: 未找到服務器配置文件 $SERVER_CONFIG"
        echo "   跳過自動配置，請手動配置 systemd 和 nginx"
        return 0
    fi
    
    echo "讀取服務器配置..."
    
    # 檢查並修復配置文件權限（確保當前用戶可以讀取）
    if [ ! -r "$SERVER_CONFIG" ]; then
        echo "修復配置文件權限..."
        CURRENT_USER=$(whoami)
        sudo chown $CURRENT_USER:$CURRENT_USER "$SERVER_CONFIG" 2>/dev/null || true
        sudo chmod 600 "$SERVER_CONFIG" 2>/dev/null || true
    fi
    
    source "$SERVER_CONFIG"
    
    # 驗證必要的配置變數
    if [ -z "$DOMAIN" ] || [ -z "$EC2_IP" ] || [ -z "$SECRET_KEY" ]; then
        echo "⚠️  警告: 服務器配置文件缺少必要變數（DOMAIN, EC2_IP, SECRET_KEY）"
        echo "   跳過自動配置"
        return 0
    fi
    
    WWW_DOMAIN=${WWW_DOMAIN:-www.$DOMAIN}
    
    echo "應用配置:"
    echo "  - 域名: $DOMAIN"
    echo "  - WWW 域名: $WWW_DOMAIN"
    echo "  - EC2 IP: $EC2_IP"
    
    # 處理 Systemd 服務文件
    SYSTEMD_SERVICE="/etc/systemd/system/climbing_system.service"
    if [ ! -f "$SYSTEMD_SERVICE" ]; then
        echo "首次部署: 複製 systemd 服務文件..."
        if [ -f "$PROJECT_DIR/Deployment/systemd/climbing_system.service" ]; then
            sudo cp "$PROJECT_DIR/Deployment/systemd/climbing_system.service" "$SYSTEMD_SERVICE"
        else
            echo "⚠️  警告: 找不到模板文件 Deployment/systemd/climbing_system.service"
        fi
    fi
    
    if [ -f "$SYSTEMD_SERVICE" ]; then
        echo "更新 systemd 服務配置..."
        # 更新環境變數
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-secret-key-here|$SECRET_KEY|g" "$SYSTEMD_SERVICE"
        
        # 修復 gunicorn_config.py 路徑（如果使用舊路徑）
        if grep -q "/var/www/Climbing_score_counter/gunicorn_config.py" "$SYSTEMD_SERVICE"; then
            echo "修復 gunicorn_config.py 路徑..."
            sudo sed -i "s|/var/www/Climbing_score_counter/gunicorn_config.py|/var/www/Climbing_score_counter/Deployment/gunicorn_config.py|g" "$SYSTEMD_SERVICE"
            echo "✅ gunicorn_config.py 路徑已修復"
        fi
        
        echo "✅ systemd 配置已更新"
    fi
    
    # 處理 Nginx 配置文件
    NGINX_AVAILABLE="/etc/nginx/sites-available/climbing_system.conf"
    NGINX_ENABLED="/etc/nginx/sites-enabled/climbing_system.conf"
    
    if [ ! -f "$NGINX_AVAILABLE" ]; then
        echo "首次部署: 複製 nginx 配置文件..."
        if [ -f "$PROJECT_DIR/Deployment/nginx/climbing_system.conf" ]; then
            sudo cp "$PROJECT_DIR/Deployment/nginx/climbing_system.conf" "$NGINX_AVAILABLE"
            # 創建符號連結
            if [ ! -L "$NGINX_ENABLED" ]; then
                sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
            fi
        else
            echo "⚠️  警告: 找不到模板文件 Deployment/nginx/climbing_system.conf"
        fi
    fi
    
    if [ -f "$NGINX_AVAILABLE" ]; then
        echo "更新 nginx 配置..."
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$NGINX_AVAILABLE"
        echo "✅ nginx 配置已更新"
    fi
}

# 檢查項目目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "錯誤: 項目目錄不存在: $PROJECT_DIR"
    echo "請先創建目錄或檢查路徑是否正確"
    exit 1
fi

# 進入項目目錄
cd $PROJECT_DIR || {
    echo "錯誤: 無法進入項目目錄: $PROJECT_DIR"
    exit 1
}

# 應用服務器配置（自動替換占位符）
apply_server_config

# 如果使用 Git，拉取最新代碼
if [ -d ".git" ]; then
    echo "拉取最新代碼..."
    
    # 解決 Git 安全目錄問題（如果項目目錄所有者與當前用戶不匹配）
    if ! git config --global --get safe.directory | grep -q "$PROJECT_DIR"; then
        echo "配置 Git 安全目錄..."
        git config --global --add safe.directory "$PROJECT_DIR"
    fi
    
    # 檢查並修復 .git 目錄權限（如果當前用戶無法寫入）
    if [ ! -w ".git/FETCH_HEAD" ] 2>/dev/null; then
        echo "修復 .git 目錄權限..."
        CURRENT_USER=$(whoami)
        sudo chown -R $CURRENT_USER:$CURRENT_USER .git 2>/dev/null || {
            echo "⚠️  警告: 無法修復 .git 目錄權限，可能需要手動執行:"
            echo "   sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR/.git"
        }
    fi
    
    # 檢查並修復項目文件權限（確保當前用戶可以更新文件）
    CURRENT_USER=$(whoami)
    if [ ! -w "." ] 2>/dev/null || [ ! -w "Deployment" ] 2>/dev/null 2>/dev/null; then
        echo "修復項目文件權限..."
        # 將當前用戶添加到 www-data 組（如果尚未添加）
        if ! groups | grep -q www-data; then
            echo "將 $CURRENT_USER 添加到 www-data 組..."
            sudo usermod -a -G www-data $CURRENT_USER 2>/dev/null || true
        fi
        # 給項目目錄添加組寫權限
        sudo chmod -R g+w "$PROJECT_DIR" 2>/dev/null || {
            echo "⚠️  警告: 無法修復項目文件權限，可能需要手動執行:"
            echo "   sudo chmod -R g+w $PROJECT_DIR"
            echo "   或: sudo chown -R $CURRENT_USER:www-data $PROJECT_DIR"
        }
    fi
    
    git fetch origin
    
    # 處理本地數據庫文件的衝突（如果存在）
    if git diff --quiet db.sqlite3 2>/dev/null; then
        # 沒有本地更改，直接重置
        git reset --hard origin/main || git reset --hard origin/master
    else
        # 有本地更改，先備份數據庫（如果存在）
        if [ -f "db.sqlite3" ]; then
            echo "備份本地數據庫文件..."
            cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
        fi
        # 強制重置，忽略本地更改
        git checkout -- db.sqlite3 2>/dev/null || true
        git reset --hard origin/main || git reset --hard origin/master
    fi
    
    echo "代碼更新完成"
    
    # Git pull 後重新應用配置（因為模板文件可能被更新）
    echo "重新應用服務器配置..."
    apply_server_config
else
    echo "警告: 未檢測到 Git 倉庫，跳過代碼更新"
fi

# 檢查並創建虛擬環境（如果不存在）
if [ ! -d "$VENV_DIR" ]; then
    echo "虛擬環境不存在，正在創建..."
    # 確保有權限創建虛擬環境目錄
    if [ ! -w "$PROJECT_DIR" ]; then
        echo "修復項目目錄權限以創建虛擬環境..."
        CURRENT_USER=$(whoami)
        sudo chmod g+w "$PROJECT_DIR" 2>/dev/null || true
    fi
    python3 -m venv $VENV_DIR
    echo "虛擬環境創建完成"
fi

# 激活虛擬環境
echo "激活虛擬環境..."
source $VENV_DIR/bin/activate

# 確保使用正確的 pip 和 python
if ! command -v pip &> /dev/null; then
    echo "錯誤: 無法找到 pip，請檢查虛擬環境"
    exit 1
fi

# 安裝/更新依賴
echo "安裝依賴..."
pip install --upgrade pip
pip install -r requirements.txt

# 運行數據庫遷移
echo "運行數據庫遷移..."
# 確保數據庫文件目錄有寫入權限
if [ -f "db.sqlite3" ] && [ ! -w "db.sqlite3" ]; then
    echo "修復數據庫文件權限..."
    sudo chmod 664 db.sqlite3 2>/dev/null || true
    sudo chown www-data:www-data db.sqlite3 2>/dev/null || true
fi
python manage.py migrate --noinput

# 創建必要的目錄（如果不存在）
echo "創建必要的目錄..."
sudo mkdir -p $PROJECT_DIR/logs
sudo mkdir -p $PROJECT_DIR/media
sudo mkdir -p $PROJECT_DIR/staticfiles
sudo mkdir -p $PROJECT_DIR/backups

# 收集靜態文件前，確保當前用戶可以寫入 staticfiles 目錄
echo "準備靜態文件目錄..."
CURRENT_USER=$(whoami)
if [ -d "$PROJECT_DIR/staticfiles" ]; then
    # 臨時設置權限，讓當前用戶可以刪除和寫入
    sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR/staticfiles 2>/dev/null || true
    sudo chmod -R 755 $PROJECT_DIR/staticfiles 2>/dev/null || true
fi

# 收集靜態文件
echo "收集靜態文件..."
python manage.py collectstatic --noinput --clear

# 設置文件權限
echo "設置文件權限..."
# 只對特定目錄設置權限，避免影響整個項目（特別是 .git 目錄）
sudo chown -R www-data:www-data $PROJECT_DIR/logs $PROJECT_DIR/media $PROJECT_DIR/staticfiles $PROJECT_DIR/backups 2>/dev/null || true
sudo chmod -R 775 $PROJECT_DIR/logs 2>/dev/null || true
sudo chmod -R 775 $PROJECT_DIR/media 2>/dev/null || true
sudo chmod -R 755 $PROJECT_DIR/staticfiles 2>/dev/null || true
sudo chmod -R 775 $PROJECT_DIR/backups 2>/dev/null || true

# 確保數據庫文件權限正確（如果存在）
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    sudo chown www-data:www-data "$PROJECT_DIR/db.sqlite3" 2>/dev/null || true
    sudo chmod 664 "$PROJECT_DIR/db.sqlite3" 2>/dev/null || true
fi

# 保護服務器配置文件（如果存在）
if [ -f "$SERVER_CONFIG" ]; then
    sudo chmod 600 "$SERVER_CONFIG" 2>/dev/null || true
    echo "✅ 服務器配置文件權限已設置"
fi

# 重啟 Gunicorn 服務
echo "重啟 Gunicorn 服務..."
sudo systemctl daemon-reload
sudo systemctl restart climbing_system

# 檢查服務狀態
echo "檢查服務狀態..."
sudo systemctl status climbing_system --no-pager

# 重載 Nginx（如果需要）
echo "重載 Nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "部署完成！"
echo "請檢查服務狀態："
echo "  - Gunicorn: sudo systemctl status climbing_system"
echo "  - Nginx: sudo systemctl status nginx"
echo "  - 日誌: tail -f $PROJECT_DIR/logs/gunicorn_error.log"

