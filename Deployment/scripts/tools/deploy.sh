#!/bin/bash
# AWS EC2 部署腳本
# 使用方法：bash Deployment/scripts/tools/deploy.sh
# 或從項目根目錄：bash Deployment/scripts/tools/deploy.sh

set -e

# 自動檢測項目根目錄
# 獲取腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 從 Deployment/scripts/tools/ 向上三層到項目根目錄
DETECTED_PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 檢查是否在服務器上（/var/www/Climbing_score_counter 存在）
# 如果不在服務器上，使用檢測到的項目根目錄
if [ -d "/var/www/Climbing_score_counter" ] && [ -f "/var/www/Climbing_score_counter/manage.py" ]; then
    # 在服務器上運行
    PROJECT_DIR="/var/www/Climbing_score_counter"
else
    # 在本地運行，使用檢測到的項目根目錄
    PROJECT_DIR="$DETECTED_PROJECT_ROOT"
    echo "ℹ️  檢測到本地環境，使用項目目錄: $PROJECT_DIR"
fi

VENV_DIR="$PROJECT_DIR/venv"
SERVER_CONFIG="$PROJECT_DIR/.server-config"

# 應用服務器配置（自動替換占位符）- 僅在服務器上執行
apply_server_config() {
    # 只在服務器環境執行
    if [ "$PROJECT_DIR" != "/var/www/Climbing_score_counter" ]; then
        echo "ℹ️  跳過服務器配置（本地環境）"
        return 0
    fi
    
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
    if [ ! -f "$SYSTEMD_SERVICE" ] && [ -f "$PROJECT_DIR/Deployment/configs/systemd/climbing_system.service" ]; then
        sudo cp "$PROJECT_DIR/Deployment/configs/systemd/climbing_system.service" "$SYSTEMD_SERVICE"
    fi
    
    if [ -f "$SYSTEMD_SERVICE" ]; then
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$SYSTEMD_SERVICE"
        sudo sed -i "s|your-secret-key-here|$SECRET_KEY|g" "$SYSTEMD_SERVICE"
        
        # 修復舊路徑
        if grep -q "/var/www/Climbing_score_counter/gunicorn_config.py" "$SYSTEMD_SERVICE"; then
            sudo sed -i "s|/var/www/Climbing_score_counter/gunicorn_config.py|/var/www/Climbing_score_counter/Deployment/configs/gunicorn_config.py|g" "$SYSTEMD_SERVICE"
        fi
    fi
    
    # 更新 Nginx 配置
    NGINX_AVAILABLE="/etc/nginx/sites-available/climbing_system.conf"
    NGINX_ENABLED="/etc/nginx/sites-enabled/climbing_system.conf"
    
    if [ ! -f "$NGINX_AVAILABLE" ] && [ -f "$PROJECT_DIR/Deployment/configs/nginx/climbing_system.conf" ]; then
        sudo cp "$PROJECT_DIR/Deployment/configs/nginx/climbing_system.conf" "$NGINX_AVAILABLE"
        [ ! -L "$NGINX_ENABLED" ] && sudo ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"
    fi
    
    if [ -f "$NGINX_AVAILABLE" ]; then
        sudo sed -i "s|your-domain.com|$DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|www.your-domain.com|$WWW_DOMAIN|g" "$NGINX_AVAILABLE"
        sudo sed -i "s|your-ec2-ip|$EC2_IP|g" "$NGINX_AVAILABLE"
    fi
}

# 檢查項目目錄
[ ! -d "$PROJECT_DIR" ] && { echo "❌ 錯誤: 項目目錄不存在: $PROJECT_DIR"; exit 1; }
[ ! -f "$PROJECT_DIR/manage.py" ] && { echo "❌ 錯誤: 未找到 manage.py，請確認項目目錄正確: $PROJECT_DIR"; exit 1; }
cd "$PROJECT_DIR" || { echo "❌ 錯誤: 無法進入項目目錄: $PROJECT_DIR"; exit 1; }
echo "📁 項目目錄: $PROJECT_DIR"

# 應用服務器配置
apply_server_config

# Git 更新
if [ -d ".git" ]; then
    echo "📥 開始 Git 更新..."
    
    # 記錄當前版本
    OLD_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "   當前版本: $OLD_COMMIT"
    
    # 配置 Git 安全目錄
    if ! git config --global --get safe.directory | grep -q "$PROJECT_DIR"; then
        git config --global --add safe.directory "$PROJECT_DIR"
        echo "   ✅ Git 安全目錄已配置"
    fi
    
    # 修復 .git 目錄權限（僅在服務器上執行）
    if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
        CURRENT_USER=$(whoami)
        if [ ! -w ".git/FETCH_HEAD" ] 2>/dev/null; then
            echo "   🔧 修復 .git 目錄權限..."
            sudo chown -R $CURRENT_USER:$CURRENT_USER .git 2>/dev/null || {
                echo "   ⚠️  警告: 無法修復 .git 目錄權限"
            }
        fi
        
        # 修復項目文件權限
        if [ ! -w "." ] 2>/dev/null || [ ! -w "Deployment" ] 2>/dev/null; then
            echo "   🔧 修復項目文件權限..."
            if ! groups | grep -q www-data; then
                sudo usermod -a -G www-data $CURRENT_USER 2>/dev/null || true
            fi
            sudo chmod -R g+w "$PROJECT_DIR" 2>/dev/null || true
        fi
    fi
    
    # 檢查遠程配置
    echo "   🔍 檢查遠程倉庫配置..."
    if ! git remote get-url origin >/dev/null 2>&1; then
        echo "   ❌ 錯誤: 未配置遠程倉庫 origin"
        exit 1
    fi
    REMOTE_URL=$(git remote get-url origin)
    echo "   遠程倉庫: $REMOTE_URL"
    
    # 獲取最新代碼
    echo "   📥 從遠程獲取最新代碼..."
    if git fetch origin 2>&1; then
        echo "   ✅ Git fetch 成功"
    else
        FETCH_EXIT_CODE=$?
        echo "   ❌ 錯誤: Git fetch 失敗，退出碼: $FETCH_EXIT_CODE"
        echo "   嘗試診斷問題..."
        git remote -v
        echo "   檢查網絡連接..."
        ping -c 2 github.com 2>/dev/null || ping -c 2 gitlab.com 2>/dev/null || echo "   ⚠️  無法連接到 Git 服務器"
        exit $FETCH_EXIT_CODE
    fi
    
    # 檢查遠程分支
    echo "   🔍 檢查遠程分支..."
    REMOTE_MAIN_COMMIT=""
    REMOTE_MASTER_COMMIT=""
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
        REMOTE_MAIN_COMMIT=$(git rev-parse --short origin/main)
        echo "   ✅ 找到遠程分支 main: $REMOTE_MAIN_COMMIT"
    fi
    if git rev-parse --verify origin/master >/dev/null 2>&1; then
        REMOTE_MASTER_COMMIT=$(git rev-parse --short origin/master)
        echo "   ✅ 找到遠程分支 master: $REMOTE_MASTER_COMMIT"
    fi
    
    if [ -z "$REMOTE_MAIN_COMMIT" ] && [ -z "$REMOTE_MASTER_COMMIT" ]; then
        echo "   ❌ 錯誤: 未找到遠程分支 main 或 master"
        echo "   可用的遠程分支:"
        git branch -r | head -10
        exit 1
    fi
    
    # 處理數據庫文件衝突
    echo "   🔍 檢查數據庫文件狀態..."
    if git diff --quiet db.sqlite3 2>/dev/null; then
        echo "   ✅ 數據庫文件無衝突"
        if [ -n "$REMOTE_MAIN_COMMIT" ]; then
            echo "   🔄 重置到 origin/main ($REMOTE_MAIN_COMMIT)..."
            if git reset --hard origin/main; then
                echo "   ✅ 已重置到 origin/main"
            else
                echo "   ❌ 錯誤: 無法重置到 origin/main"
                exit 1
            fi
        elif [ -n "$REMOTE_MASTER_COMMIT" ]; then
            echo "   🔄 重置到 origin/master ($REMOTE_MASTER_COMMIT)..."
            if git reset --hard origin/master; then
                echo "   ✅ 已重置到 origin/master"
            else
                echo "   ❌ 錯誤: 無法重置到 origin/master"
                exit 1
            fi
        fi
    else
        echo "   ⚠️  檢測到數據庫文件有本地修改"
        if [ -f "db.sqlite3" ]; then
            mkdir -p backups
            BACKUP_NAME="backups/db_local_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
            cp db.sqlite3 "$BACKUP_NAME" 2>/dev/null || true
            echo "   💾 數據庫已備份到: $BACKUP_NAME"
        fi
        echo "   🔄 重置數據庫文件..."
        git checkout -- db.sqlite3 2>/dev/null || true
        
        if [ -n "$REMOTE_MAIN_COMMIT" ]; then
            echo "   🔄 重置到 origin/main ($REMOTE_MAIN_COMMIT)..."
            if git reset --hard origin/main; then
                echo "   ✅ 已重置到 origin/main"
            else
                echo "   ❌ 錯誤: 無法重置到 origin/main"
                exit 1
            fi
        elif [ -n "$REMOTE_MASTER_COMMIT" ]; then
            echo "   🔄 重置到 origin/master ($REMOTE_MASTER_COMMIT)..."
            if git reset --hard origin/master; then
                echo "   ✅ 已重置到 origin/master"
            else
                echo "   ❌ 錯誤: 無法重置到 origin/master"
                exit 1
            fi
        fi
        
        if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
            echo "   ℹ️  提示：從服務器同步數據庫: bash Deployment/scripts/tools/sync_database_from_server.sh"
        fi
    fi
    
    # 驗證更新結果
    NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "   更新後版本: $NEW_COMMIT"
    
    if [ "$OLD_COMMIT" != "unknown" ] && [ "$NEW_COMMIT" != "unknown" ]; then
        if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
            echo "   ℹ️  代碼版本未變更（已是最新版本）"
        else
            echo "   ✅ 代碼已更新: $OLD_COMMIT -> $NEW_COMMIT"
            echo "   最新提交信息:"
            git log -1 --oneline 2>/dev/null || true
        fi
    fi
    
    # 檢查是否有未提交的修改
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        echo "   ⚠️  警告: 檢測到未提交的修改"
        echo "   未提交的文件:"
        git status --short | head -10
    fi
    
    # 重新應用配置（模板文件可能已更新）- 僅在服務器上執行
    if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
        apply_server_config
    fi
    
    echo "✅ Git 更新完成"
else
    echo "⚠️  警告: 未檢測到 Git 倉庫，跳過代碼更新"
fi

# 創建虛擬環境
if [ ! -d "$VENV_DIR" ]; then
    if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
        if [ ! -w "$PROJECT_DIR" ]; then
            CURRENT_USER=$(whoami)
            sudo chmod g+w "$PROJECT_DIR" 2>/dev/null || true
        fi
    fi
    python3 -m venv $VENV_DIR
fi

# 激活虛擬環境
source $VENV_DIR/bin/activate

# 安裝系統依賴（pyheif）- 僅在服務器上執行
if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
    sudo apt-get update -qq
    sudo apt-get install -y libheif-dev libde265-dev libjpeg-dev zlib1g-dev 2>/dev/null || true
else
    echo "ℹ️  跳過系統依賴安裝（本地環境）"
fi

# 安裝 Python 依賴
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 數據庫遷移
python manage.py makemigrations --noinput || true
if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
    if [ -f "db.sqlite3" ] && [ ! -w "db.sqlite3" ]; then
        sudo chmod 664 db.sqlite3 2>/dev/null || true
        sudo chown www-data:www-data db.sqlite3 2>/dev/null || true
    fi
fi
python manage.py migrate --noinput

# 創建必要目錄
if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
    sudo mkdir -p $PROJECT_DIR/{logs,media,staticfiles,backups}
else
    mkdir -p $PROJECT_DIR/{logs,media,staticfiles,backups}
fi

# 收集靜態文件
CURRENT_USER=$(whoami)
if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
    if [ -d "$PROJECT_DIR/staticfiles" ]; then
        sudo chown -R $CURRENT_USER:$CURRENT_USER $PROJECT_DIR/staticfiles 2>/dev/null || true
        sudo chmod -R 755 $PROJECT_DIR/staticfiles 2>/dev/null || true
    fi
fi
python manage.py collectstatic --noinput --clear

# 設置文件權限（僅在服務器上執行）
if [ "$PROJECT_DIR" = "/var/www/Climbing_score_counter" ]; then
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
else
    echo "ℹ️  跳過服務器權限設置和服務重啟（本地環境）"
fi

echo "✅ 部署完成"
