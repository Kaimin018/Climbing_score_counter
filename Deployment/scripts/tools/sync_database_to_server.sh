#!/bin/bash
# 將本地數據庫同步到 AWS EC2 服務器
# 使用方法：bash Deployment/sync_database_to_server.sh
# 
# ⚠️  警告：此操作會覆蓋服務器上的數據庫！
# 請確保在執行前已備份服務器數據庫

set -e  # 遇到錯誤立即退出

echo "=========================================="
echo "將本地數據庫同步到 AWS EC2 服務器"
echo "=========================================="

# 配置（請根據實際情況修改）
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-your-ec2-ip}"
EC2_KEY="${EC2_KEY:-~/.ssh/your-key.pem}"
PROJECT_DIR="/var/www/Climbing_score_counter"
REMOTE_DB="$PROJECT_DIR/db.sqlite3"
LOCAL_DB="db.sqlite3"
REMOTE_BACKUP_DIR="$PROJECT_DIR/backups"

# 檢查必要的環境變數
if [ "$EC2_HOST" = "your-ec2-ip" ]; then
    echo "⚠️  錯誤: 請設置 EC2_HOST 環境變數"
    echo "   使用方法:"
    echo "   export EC2_HOST=3.26.6.19"
    echo "   export EC2_KEY=~/.ssh/your-key.pem"
    echo "   bash Deployment/sync_database_to_server.sh"
    exit 1
fi

# 檢查本地數據庫是否存在
if [ ! -f "$LOCAL_DB" ]; then
    echo "❌ 本地數據庫不存在: $LOCAL_DB"
    exit 1
fi

# 確認操作
echo "⚠️  警告：此操作會覆蓋服務器上的數據庫！"
echo "   服務器: $EC2_USER@$EC2_HOST"
echo "   目標文件: $REMOTE_DB"
echo ""
read -p "確定要繼續嗎？(yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

# 檢查 SSH 連接
echo "檢查 SSH 連接..."
if ! ssh -i "$EC2_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo '連接成功'" 2>/dev/null; then
    echo "❌ 無法連接到服務器 $EC2_USER@$EC2_HOST"
    exit 1
fi

# 在服務器上備份現有數據庫
echo "在服務器上備份現有數據庫..."
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "
    if [ -f $REMOTE_DB ]; then
        mkdir -p $REMOTE_BACKUP_DIR
        BACKUP_NAME=$REMOTE_BACKUP_DIR/db_backup_before_sync_\$(date +%Y%m%d_%H%M%S).sqlite3
        sudo cp $REMOTE_DB \$BACKUP_NAME
        sudo chown \$USER:\$USER \$BACKUP_NAME
        echo \"✅ 服務器數據庫已備份到: \$BACKUP_NAME\"
    else
        echo \"ℹ️  服務器數據庫不存在，跳過備份\"
    fi
"

# 上傳本地數據庫
echo "上傳本地數據庫到服務器..."
scp -i "$EC2_KEY" "$LOCAL_DB" "$EC2_USER@$EC2_HOST:$REMOTE_DB"

# 設置服務器上的文件權限
echo "設置服務器文件權限..."
ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "
    sudo chown www-data:www-data $REMOTE_DB
    sudo chmod 664 $REMOTE_DB
    echo \"✅ 文件權限已設置\"
"

# 重啟 Gunicorn 服務（可選）
echo ""
read -p "是否重啟 Gunicorn 服務以應用更改？(yes/no): " RESTART_SERVICE

if [ "$RESTART_SERVICE" = "yes" ]; then
    echo "重啟 Gunicorn 服務..."
    ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "sudo systemctl restart climbing_system"
    echo "✅ 服務已重啟"
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
echo ""
echo "⚠️  注意事項:"
echo "   1. 服務器數據庫已備份到: $REMOTE_BACKUP_DIR/"
echo "   2. 如果遇到問題，可以從備份恢復"
echo ""

