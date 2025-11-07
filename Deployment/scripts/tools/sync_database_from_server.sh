#!/bin/bash
# 從 AWS EC2 服務器同步數據庫到本地
# 使用方法：bash Deployment/sync_database_from_server.sh

set -e  # 遇到錯誤立即退出

echo "=========================================="
echo "從 AWS EC2 同步數據庫到本地"
echo "=========================================="

# 從 EC2_security_config 文件導入配置（如果存在）
CONFIG_FILE="security/EC2_security_config"
if [ -f "$CONFIG_FILE" ]; then
    echo "從配置文件讀取設置: $CONFIG_FILE"
    # 讀取配置（跳過註釋行和空行）
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # 跳過註釋行和空行
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        
        # 去除前後空格
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # 確保值不為空
        [[ -z "$value" ]] && continue
        
        case "$key" in
            EC2_HOST)
                EC2_HOST="$value"
                ;;
            EC2_KEY)
                # 將 Windows 路徑轉換為 Unix 路徑
                # 先將反斜線轉換為正斜線（使用 sed 確保正確轉換）
                value=$(echo "$value" | sed 's/\\/\//g')
                # 處理 %USERPROFILE% 或 $USERPROFILE$ 轉換為 $HOME
                value="${value//%USERPROFILE%/$HOME}"
                value="${value//\$USERPROFILE\$/$HOME}"
                # 如果是相對路徑，轉換為絕對路徑（基於項目根目錄）
                if [[ "$value" != /* ]] && [[ "$value" != ~* ]]; then
                    # 獲取腳本所在目錄的父目錄（項目根目錄）
                    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
                    # 確保路徑之間有斜線分隔符
                    value="$PROJECT_ROOT/$value"
                fi
                EC2_KEY="$value"
                ;;
            EC2_USER)
                EC2_USER="$value"
                ;;
        esac
    done < "$CONFIG_FILE"
fi

# 配置（如果環境變數或配置文件未設置，使用默認值）
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-your-ec2-ip}"
EC2_KEY="${EC2_KEY:-~/.ssh/your-key.pem}"
PROJECT_DIR="/var/www/Climbing_score_counter"
REMOTE_DB="$PROJECT_DIR/db.sqlite3"
LOCAL_DB="db.sqlite3"
BACKUP_DIR="backups"

# 顯示配置信息
echo ""
echo "配置信息:"
echo "  EC2_HOST: $EC2_HOST"
echo "  EC2_KEY: $EC2_KEY"
echo "  EC2_USER: $EC2_USER"
echo ""

# 檢查必要的配置
if [ "$EC2_HOST" = "your-ec2-ip" ] || [ -z "$EC2_HOST" ]; then
    echo "⚠️  錯誤: 請設置 EC2_HOST"
    echo "   方法1: 在 security/EC2_security_config 文件中設置"
    echo "   方法2: 使用環境變數:"
    echo "   export EC2_HOST=3.26.6.19"
    echo "   export EC2_KEY=~/.ssh/your-key.pem"
    echo "   bash Deployment/sync_database_from_server.sh"
    exit 1
fi

# 展開 ~ 路徑
EC2_KEY="${EC2_KEY/#\~/$HOME}"

# 檢查 SSH 連接
echo "檢查 SSH 連接..."
if ! ssh -i "$EC2_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo '連接成功'" 2>/dev/null; then
    echo "❌ 無法連接到服務器 $EC2_USER@$EC2_HOST"
    echo "   請檢查："
    echo "   1. EC2_HOST 是否正確"
    echo "   2. EC2_KEY 路徑是否正確"
    echo "   3. SSH 密鑰權限是否正確 (chmod 600)"
    exit 1
fi

# 檢查遠程數據庫是否存在
echo "檢查遠程數據庫..."
if ! ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "[ -f $REMOTE_DB ]"; then
    echo "❌ 遠程數據庫不存在: $REMOTE_DB"
    exit 1
fi

# 創建本地備份目錄
mkdir -p "$BACKUP_DIR"

# 備份本地數據庫（如果存在）
if [ -f "$LOCAL_DB" ]; then
    BACKUP_NAME="$BACKUP_DIR/db_local_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
    echo "備份本地數據庫到: $BACKUP_NAME"
    cp "$LOCAL_DB" "$BACKUP_NAME"
    echo "✅ 本地數據庫已備份"
else
    echo "ℹ️  本地數據庫不存在，跳過備份"
fi

# 下載遠程數據庫
echo "下載遠程數據庫..."
scp -i "$EC2_KEY" "$EC2_USER@$EC2_HOST:$REMOTE_DB" "$LOCAL_DB"

# 檢查下載是否成功
if [ -f "$LOCAL_DB" ]; then
    FILE_SIZE=$(du -h "$LOCAL_DB" | cut -f1)
    echo "✅ 數據庫下載成功！"
    echo "   文件大小: $FILE_SIZE"
    echo "   位置: $LOCAL_DB"
    
    # 顯示數據庫基本信息
    echo ""
    echo "數據庫信息:"
    if command -v sqlite3 &> /dev/null; then
        echo "   表數量: $(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "N/A")"
    fi
else
    echo "❌ 數據庫下載失敗"
    exit 1
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
echo ""
echo "⚠️  注意事項:"
echo "   1. 本地數據庫已備份到: $BACKUP_DIR/"
echo "   2. 如果遇到問題，可以從備份恢復"
echo "   3. 建議在同步前先停止本地開發服務器"
echo ""

