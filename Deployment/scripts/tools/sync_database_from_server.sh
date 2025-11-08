#!/bin/bash
# 從 AWS EC2 服務器同步數據庫到本地
# 使用方法：bash Deployment/sync_database_from_server.sh

set -e  # 遇到錯誤立即退出

echo "=========================================="
echo "從 AWS EC2 同步數據庫到本地"
echo "=========================================="

# 從 EC2_security_config 文件導入配置（如果存在）
# 注意：環境變數會優先於配置文件（在後面使用 ${VAR:-default} 語法）
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
                # 只有當環境變數未設置時才從配置文件讀取
                if [ -z "$EC2_HOST" ]; then
                    EC2_HOST="$value"
                fi
                ;;
            EC2_KEY)
                # 只有當環境變數未設置時才從配置文件讀取
                if [ -z "$EC2_KEY" ]; then
                    # 將 Windows 路徑轉換為 Unix 路徑
                    # 先將反斜線轉換為正斜線（使用 sed 確保正確轉換）
                    value=$(echo "$value" | sed 's/\\/\//g')
                    # 處理 %USERPROFILE% 或 $USERPROFILE$ 轉換為 $HOME
                    value="${value//%USERPROFILE%/$HOME}"
                    value="${value//\$USERPROFILE\$/$HOME}"
                    # 如果是相對路徑，轉換為絕對路徑（基於項目根目錄）
                    if [[ "$value" != /* ]] && [[ "$value" != ~* ]]; then
                        # 獲取腳本所在目錄，然後向上三層到項目根目錄
                        # 腳本在 Deployment/scripts/tools/，需要向上三層到項目根目錄
                        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                        PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
                        # 確保路徑之間有斜線分隔符
                        value="$PROJECT_ROOT/$value"
                    fi
                    EC2_KEY="$value"
                fi
                ;;
            EC2_USER)
                # 只有當環境變數未設置時才從配置文件讀取
                if [ -z "$EC2_USER" ]; then
                    EC2_USER="$value"
                fi
                ;;
        esac
    done < "$CONFIG_FILE"
fi

# 配置（如果環境變數或配置文件未設置，使用默認值）
EC2_USER="${EC2_USER:-ubuntu}"
EC2_HOST="${EC2_HOST:-your-ec2-ip}"
EC2_KEY="${EC2_KEY:-~/.ssh/your-key.pem}"

# 如果 EC2_KEY 是從環境變數傳入的 Windows 路徑，需要轉換為 Unix 路徑
# 檢查是否是 Windows 路徑格式（包含反斜線或驅動器字母）
# 注意：批處理腳本已經將路徑轉換為 Git Bash 格式，但這裡保留轉換邏輯以防直接調用
if [[ "$EC2_KEY" =~ ^[A-Za-z]: ]] || [[ "$EC2_KEY" == *\\* ]]; then
    # 將 Windows 路徑轉換為 Unix 路徑
    # 先將反斜線轉換為正斜線
    EC2_KEY=$(echo "$EC2_KEY" | sed 's/\\/\//g')
    # 如果是 Windows 路徑（如 D:/path），轉換為 Git Bash 路徑格式（/d/path）
    if [[ "$EC2_KEY" =~ ^([A-Za-z]):(.*)$ ]]; then
        DRIVE_LETTER="${BASH_REMATCH[1]}"
        PATH_PART="${BASH_REMATCH[2]}"
        # 轉換為小寫並添加前綴
        DRIVE_LOWER=$(echo "$DRIVE_LETTER" | tr '[:upper:]' '[:lower:]')
        # 確保路徑部分以 / 開頭（如果沒有）
        if [[ ! "$PATH_PART" =~ ^/ ]]; then
            PATH_PART="/$PATH_PART"
        fi
        EC2_KEY="/$DRIVE_LOWER$PATH_PART"
    fi
fi

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

# 如果路徑是 /d/... 格式（Git Bash），但文件不存在，嘗試 WSL 格式 /mnt/d/...
if [[ "$EC2_KEY" =~ ^/[a-z]/ ]] && [ ! -f "$EC2_KEY" ]; then
    # Extract drive letter and path
    if [[ "$EC2_KEY" =~ ^/([a-z])(.*)$ ]]; then
        DRIVE="${BASH_REMATCH[1]}"
        PATH_PART="${BASH_REMATCH[2]}"
        WSL_PATH="/mnt/$DRIVE$PATH_PART"
        # Try WSL path format
        if [ -f "$WSL_PATH" ]; then
            echo "ℹ️  檢測到 WSL 環境，使用路徑: $WSL_PATH"
            EC2_KEY="$WSL_PATH"
        fi
    fi
fi

# Debug: Show the key path being checked (remove debug output in production)
# echo "[DEBUG] Checking key file: $EC2_KEY"

# 檢查密鑰文件是否存在
# Use quotes to handle paths with spaces
if [ ! -f "$EC2_KEY" ]; then
    echo "❌ 錯誤: 密鑰文件不存在: $EC2_KEY"
    echo ""
    echo "   請確認："
    echo "   1. 密鑰文件路徑是否正確"
    echo "   2. 密鑰文件是否已下載到本地"
    echo "   3. 如果使用相對路徑，請確保路徑相對於項目根目錄"
    echo ""
    echo "   預期位置: security/climbing_score_counting_key.pem"
    echo "   或絕對路徑: $EC2_KEY"
    echo ""
    echo "   如果密鑰文件在其他位置，請："
    echo "   1. 將密鑰文件複製到 security/ 目錄"
    echo "   2. 或在 security/EC2_security_config 中更新 EC2_KEY 路徑"
    exit 1
fi

# 檢查密鑰文件權限（建議為 600）
KEY_PERM=$(stat -c "%a" "$EC2_KEY" 2>/dev/null || stat -f "%OLp" "$EC2_KEY" 2>/dev/null || echo "unknown")
if [ "$KEY_PERM" != "600" ] && [ "$KEY_PERM" != "400" ]; then
    echo "⚠️  警告: 密鑰文件權限為 $KEY_PERM，建議設置為 600"
    echo "   正在自動修復權限..."
    chmod 600 "$EC2_KEY" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ 權限已更新為 600"
    else
        echo "   ⚠️  無法自動更新權限，請手動執行: chmod 600 \"$EC2_KEY\""
    fi
fi

# 檢查 SSH 連接
echo "檢查 SSH 連接..."
# Try SSH connection and capture both stdout and stderr
SSH_OUTPUT=$(ssh -i "$EC2_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "echo '連接成功'" 2>&1)
SSH_EXIT_CODE=$?

if [ $SSH_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ 無法連接到服務器 $EC2_USER@$EC2_HOST"
    echo ""
    echo "   SSH 錯誤信息:"
    if [ -n "$SSH_OUTPUT" ]; then
        echo "$SSH_OUTPUT" | while IFS= read -r line; do
            echo "   $line"
        done
    else
        echo "   (無詳細錯誤信息，可能是連接超時或網絡問題)"
    fi
    echo ""
    echo "   請檢查："
    echo "   1. EC2_HOST 是否正確: $EC2_HOST"
    echo "   2. EC2_KEY 路徑是否正確: $EC2_KEY"
    echo "   3. 密鑰文件是否存在: $([ -f "$EC2_KEY" ] && echo "是" || echo "否")"
    echo "   4. SSH 密鑰權限是否正確 (chmod 600): $KEY_PERM"
    echo "   5. 網絡連接是否正常: ping $EC2_HOST"
    echo "   6. 密鑰文件是否與 EC2 實例匹配"
    echo ""
    exit 1
fi
echo "✅ SSH 連接成功"

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

