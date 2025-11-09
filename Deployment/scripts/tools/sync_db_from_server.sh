#!/bin/bash
# 從 AWS EC2 服務器同步數據庫到本地
# 使用方法：bash Deployment/scripts/tools/sync_db_from_server.sh
# 配置文件：security/EC2_security_config

# 獲取腳本目錄和項目根目錄（用於處理相對路徑）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT" || {
    echo "❌ 錯誤: 無法切換到項目根目錄: $PROJECT_ROOT"
    exit 1
}

echo "=========================================="
echo "從 AWS EC2 同步數據庫到本地"
echo "=========================================="
echo "當前目錄: $(pwd)"
echo "項目根目錄: $PROJECT_ROOT"

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
                EC2_HOST=$(echo "$value" | sed "s/^[\"']//; s/[\"']$//; s/\r$//; s/\n$//" | tr -d '\r\n')
                ;;
            EC2_KEY)
                value=$(echo "$value" | sed "s/^[\"']//; s/[\"']$//; s/\r$//; s/\n$//" | tr -d '\r\n')
                if [[ "$value" != /* ]] && [[ "$value" != ~* ]]; then
                    EC2_KEY="$PROJECT_ROOT/$value"
                else
                    EC2_KEY="$value"
                fi
                EC2_KEY="${EC2_KEY/#\~/$HOME}"
                ;;
            EC2_USER)
                EC2_USER=$(echo "$value" | sed "s/^[\"']//; s/[\"']$//; s/\r$//; s/\n$//" | tr -d '\r\n')
                ;;
            DB_FILE_PATH)
                REMOTE_DB=$(echo "$value" | sed "s/^[\"']//; s/[\"']$//; s/\r$//; s/\n$//" | tr -d '\r\n')
                ;;
        esac
    done < "$CONFIG_FILE"
fi

# 如果配置未找到，使用默認值或環境變數
EC2_HOST="${EC2_HOST:-}"
EC2_KEY="${EC2_KEY:-}"
EC2_USER="${EC2_USER:-ubuntu}"
REMOTE_DB="${REMOTE_DB:-/var/www/Climbing_score_counter/db.sqlite3}"

echo ""
echo "配置信息:"
echo "  EC2_HOST: ${EC2_HOST:-未設置}"
echo "  EC2_KEY: ${EC2_KEY:-未設置}"
echo "  EC2_USER: $EC2_USER"
echo "  REMOTE_DB: $REMOTE_DB"
echo ""

# 檢查必要的配置
if [ -z "$EC2_HOST" ] || [ "$EC2_HOST" = "your-ec2-ip" ] || [ "$EC2_HOST" = "your-ec2-ip-address" ]; then
    echo "⚠️  錯誤: 請設置 EC2_HOST"
    exit 1
fi

if [ -z "$EC2_KEY" ] || [ "$EC2_KEY" = "security/your-key-file.pem" ]; then
    echo "⚠️  錯誤: 請設置 EC2_KEY"
    exit 1
fi

# 檢查密鑰文件是否存在
if [ ! -f "$EC2_KEY" ]; then
    echo "❌ 錯誤: 密鑰文件不存在: $EC2_KEY"
    exit 1
fi

# 檢查 SSH 是否可用
if ! command -v ssh &> /dev/null; then
    echo "❌ 錯誤: SSH 客戶端未安裝"
    exit 1
fi

# 檢查 SCP 是否可用
if ! command -v scp &> /dev/null; then
    echo "❌ 錯誤: SCP 客戶端未安裝"
    exit 1
fi

# 檢查 SSH 連接
echo "檢查 SSH 連接..."
if ! ssh -i "$EC2_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "echo '連接成功'" &>/dev/null; then
    echo "❌ 無法連接到服務器 $EC2_USER@$EC2_HOST"
    exit 1
fi
echo "✅ SSH 連接成功"

# 檢查遠程數據庫是否存在且可讀
echo "檢查遠程數據庫..."
# 使用單引號包裹遠程命令，避免路徑中的特殊字符問題
REMOTE_CHECK_CMD="[ -f '$REMOTE_DB' ] && [ -r '$REMOTE_DB' ]"
if ! ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_CHECK_CMD"; then
    echo "❌ 遠程數據庫不存在或不可讀: $REMOTE_DB"
    echo "   請確保用戶 $EC2_USER 具有讀取權限。"
    exit 1
fi
echo "✅ 遠程數據庫存在且可讀"

# 創建本地備份目錄
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# 備份本地數據庫（如果存在）
LOCAL_DB="db.sqlite3"
if [ -f "$LOCAL_DB" ]; then
    BACKUP_NAME="$BACKUP_DIR/db_local_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
    echo "備份本地數據庫到: $BACKUP_NAME"
    cp "$LOCAL_DB" "$BACKUP_NAME"
    if [ $? -eq 0 ]; then
        echo "✅ 本地數據庫已備份"
    fi
fi

# 下載遠程數據庫
echo ""
echo "下載遠程數據庫..."
echo "   從: $EC2_USER@$EC2_HOST:$REMOTE_DB"
echo "   到: $LOCAL_DB"

# 執行 SCP 下載（確保遠程路徑正確處理）
echo "   執行 SCP 命令..."
# 構建遠程路徑（使用變數拼接，避免引號問題）
REMOTE_SOURCE="$EC2_USER@$EC2_HOST:$REMOTE_DB"
SCP_OUTPUT=$(scp -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$REMOTE_SOURCE" "$LOCAL_DB" 2>&1)
SCP_EXIT_CODE=$?

if [ $SCP_EXIT_CODE -ne 0 ]; then
    echo "❌ 數據庫下載失敗，退出代碼: $SCP_EXIT_CODE"
    if [ -n "$SCP_OUTPUT" ]; then
        echo "   SCP 錯誤輸出: $SCP_OUTPUT"
    fi
    exit 1
fi

# 顯示 SCP 輸出（如果有）
if [ -n "$SCP_OUTPUT" ]; then
    echo "   SCP 輸出: $SCP_OUTPUT"
fi

# 檢查下載是否成功（嚴格檢查文件存在和大小）
if [ -f "$LOCAL_DB" ]; then
    FILE_SIZE=$(stat -f%z "$LOCAL_DB" 2>/dev/null || stat -c%s "$LOCAL_DB" 2>/dev/null || echo "0")
    
    # 確保文件大小大於 0
    if [ "$FILE_SIZE" -gt 0 ] 2>/dev/null; then
        FILE_SIZE_KB=$((FILE_SIZE / 1024))
        FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
        
        if [ $FILE_SIZE_MB -gt 0 ]; then
            echo "✅ 數據庫下載成功！"
            echo "   文件大小: ${FILE_SIZE_MB} MB"
        else
            echo "✅ 數據庫下載成功！"
            echo "   文件大小: ${FILE_SIZE_KB} KB"
        fi
        echo "   位置: $LOCAL_DB"
        
        # 顯示數據庫基本信息
        echo ""
        echo "數據庫信息:"
        if command -v sqlite3 &> /dev/null; then
            TABLE_COUNT=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "N/A")
            echo "   表數量: $TABLE_COUNT"
        fi
    else
        echo "❌ 數據庫下載失敗 - 文件為空 (0 字節)"
        echo "   請檢查遠程文件 $REMOTE_DB 是否為空或路徑是否有誤"
        echo "   遠程文件大小檢查:"
        REMOTE_SIZE_CMD="stat -c%s '$REMOTE_DB' 2>/dev/null || stat -f%z '$REMOTE_DB' 2>/dev/null || echo '無法獲取'"
        REMOTE_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_SIZE_CMD")
        echo "   遠程文件大小: $REMOTE_SIZE 字節"
        exit 1
    fi
else
    echo "❌ 數據庫下載失敗 - 本地文件 $LOCAL_DB 不存在"
    exit 1
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
