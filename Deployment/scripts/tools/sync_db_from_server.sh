#!/bin/bash
# 從 AWS EC2 服務器同步數據庫和媒體庫到本地
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
echo "從 AWS EC2 同步數據庫和媒體庫到本地"
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
            MEDIA_DIR_PATH)
                REMOTE_MEDIA=$(echo "$value" | sed "s/^[\"']//; s/[\"']$//; s/\r$//; s/\n$//" | tr -d '\r\n')
                ;;
        esac
    done < "$CONFIG_FILE"
fi

# 如果配置未找到，使用默認值或環境變數
EC2_HOST="${EC2_HOST:-}"
EC2_KEY="${EC2_KEY:-}"
EC2_USER="${EC2_USER:-ubuntu}"
REMOTE_DB="${REMOTE_DB:-/var/www/Climbing_score_counter/db.sqlite3}"
REMOTE_MEDIA="${REMOTE_MEDIA:-/var/www/Climbing_score_counter/media}"
# 只同步 route_photos 目錄
REMOTE_ROUTE_PHOTOS="${REMOTE_MEDIA}/route_photos"

echo ""
echo "配置信息:"
echo "  EC2_HOST: ${EC2_HOST:-未設置}"
echo "  EC2_KEY: ${EC2_KEY:-未設置}"
echo "  EC2_USER: $EC2_USER"
echo "  REMOTE_DB: $REMOTE_DB"
echo "  REMOTE_MEDIA: $REMOTE_MEDIA"
echo "  REMOTE_ROUTE_PHOTOS: $REMOTE_ROUTE_PHOTOS"
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

# 檢查密鑰文件權限（僅 Linux/macOS）
CURRENT_PERM=$(stat -c "%a" "$EC2_KEY" 2>/dev/null || stat -f "%OLp" "$EC2_KEY" 2>/dev/null || echo "unknown")
if [ "$CURRENT_PERM" != "600" ] && [ "$CURRENT_PERM" != "unknown" ]; then
    echo "檢查密鑰文件權限..."
    echo "   當前權限: $CURRENT_PERM（需要 600）"
    echo "   正在修復權限..."
    chmod 600 "$EC2_KEY" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ 密鑰文件權限已修復為 600"
    else
        echo "   ⚠️  警告: 無法自動修復權限，請手動執行: chmod 600 \"$EC2_KEY\""
    fi
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

# 檢查 RSYNC 是否可用（優先使用，支持增量同步）
USE_RSYNC=false
if command -v rsync &> /dev/null; then
    USE_RSYNC=true
    echo "ℹ️  檢測到 rsync，將使用 rsync 同步媒體庫（支持增量同步）"
else
    echo "ℹ️  未檢測到 rsync，將使用 scp 同步媒體庫"
fi

# 檢查 SSH 連接
echo ""
echo "檢查 SSH 連接..."
SSH_TEST_OUTPUT=$(ssh -i "$EC2_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "echo '連接成功'" 2>&1)
SSH_TEST_EXIT_CODE=$?

if [ $SSH_TEST_EXIT_CODE -ne 0 ]; then
    echo "❌ 無法連接到服務器 $EC2_USER@$EC2_HOST"
    echo "   退出代碼: $SSH_TEST_EXIT_CODE"
    if [ -n "$SSH_TEST_OUTPUT" ]; then
        echo "   錯誤信息:"
        echo "$SSH_TEST_OUTPUT" | sed 's/^/   /'
    fi
    echo ""
    echo "   提示: 請檢查："
    echo "   1. 服務器是否運行中"
    echo "   2. 網絡連接是否正常"
    echo "   3. 密鑰文件路徑是否正確: $EC2_KEY"
    if [ "$IS_WINDOWS" = true ]; then
        echo "   4. 密鑰文件權限（Windows 環境）"
        echo "      如果權限錯誤，請在 PowerShell 中執行："
        echo "      icacls \"$WIN_KEY_PATH\" /inheritance:r /grant:r \"${WIN_USER}:(R)\""
    else
        echo "   4. 密鑰文件權限是否正確（應為 600）"
    fi
    echo "   5. 可以嘗試手動連接: ssh -i \"$EC2_KEY\" $EC2_USER@$EC2_HOST"
    exit 1
fi
echo "✅ SSH 連接成功"

# 檢查遠程數據庫是否存在且可讀
echo ""
echo "檢查遠程數據庫..."
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

# 獲取遠程文件大小（用於顯示進度）
REMOTE_SIZE_CMD="stat -c%s '$REMOTE_DB' 2>/dev/null || stat -f%z '$REMOTE_DB' 2>/dev/null || echo '0'"
REMOTE_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_SIZE_CMD" 2>/dev/null || echo "0")

# 執行 SCP 下載（帶進度顯示）
REMOTE_SOURCE="$EC2_USER@$EC2_HOST:$REMOTE_DB"

# 執行下載並顯示進度
if command -v pv &> /dev/null && [ "$REMOTE_SIZE" != "0" ] && [ "$REMOTE_SIZE" != "無法獲取" ] && [ "$REMOTE_SIZE" -gt 0 ] 2>/dev/null; then
    # 使用 pv 顯示進度條（最佳體驗）
    echo "   使用 pv 顯示下載進度..."
    ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "cat '$REMOTE_DB'" 2>/dev/null | \
        pv -s "$REMOTE_SIZE" -p -t -e -r -b > "$LOCAL_DB"
    SCP_EXIT_CODE=$?
    SCP_OUTPUT=""
elif [ "$REMOTE_SIZE" != "0" ] && [ "$REMOTE_SIZE" != "無法獲取" ] && [ "$REMOTE_SIZE" -gt 0 ] 2>/dev/null; then
    # 使用文件大小監控顯示進度
    echo "   執行 SCP 命令..."
    echo "   文件大小: $((REMOTE_SIZE / 1024)) KB"
    
    # 在後台執行 scp，同時監控文件大小變化
    scp -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$REMOTE_SOURCE" "$LOCAL_DB" >/dev/null 2>&1 &
    SCP_PID=$!
    
    # 監控進度
    while kill -0 $SCP_PID 2>/dev/null; do
        if [ -f "$LOCAL_DB" ]; then
            CURRENT_SIZE=$(stat -f%z "$LOCAL_DB" 2>/dev/null || stat -c%s "$LOCAL_DB" 2>/dev/null || echo "0")
            if [ "$CURRENT_SIZE" -gt 0 ] 2>/dev/null && [ "$REMOTE_SIZE" -gt 0 ] 2>/dev/null; then
                PERCENT=$((CURRENT_SIZE * 100 / REMOTE_SIZE))
                if [ $PERCENT -gt 100 ]; then
                    PERCENT=100
                fi
                BAR_LENGTH=50
                FILLED=$((PERCENT * BAR_LENGTH / 100))
                BAR=$(printf "%*s" $FILLED | tr ' ' '=')
                printf "\r   進度: [%-${BAR_LENGTH}s] %3d%% (%d/%d KB)" "$BAR" "$PERCENT" "$((CURRENT_SIZE / 1024))" "$((REMOTE_SIZE / 1024))"
            fi
        fi
        sleep 0.5
    done
    
    wait $SCP_PID
    SCP_EXIT_CODE=$?
    echo ""  # 換行
    SCP_OUTPUT=""
else
    # 無法獲取大小，使用普通 scp
    echo "   執行 SCP 命令..."
    SCP_OUTPUT=$(scp -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$REMOTE_SOURCE" "$LOCAL_DB" 2>&1)
    SCP_EXIT_CODE=$?
fi

if [ $SCP_EXIT_CODE -ne 0 ]; then
    echo "❌ 數據庫下載失敗，退出代碼: $SCP_EXIT_CODE"
    if [ -n "$SCP_OUTPUT" ]; then
        echo "   SCP 錯誤輸出:"
        echo "$SCP_OUTPUT" | sed 's/^/   /'
    fi
    exit 1
fi

# 檢查下載是否成功
if [ -f "$LOCAL_DB" ]; then
    FILE_SIZE=$(stat -f%z "$LOCAL_DB" 2>/dev/null || stat -c%s "$LOCAL_DB" 2>/dev/null || echo "0")
    
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
        REMOTE_SIZE_CMD="stat -c%s '$REMOTE_DB' 2>/dev/null || stat -f%z '$REMOTE_DB' 2>/dev/null || echo '無法獲取'"
        REMOTE_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_SIZE_CMD")
        echo "   遠程文件大小: $REMOTE_SIZE 字節"
        exit 1
    fi
else
    echo "❌ 數據庫下載失敗 - 本地文件 $LOCAL_DB 不存在"
    exit 1
fi

# 同步媒體庫（只同步 route_photos 目錄）
echo ""
echo "=========================================="
echo "同步媒體庫（route_photos）..."
echo "=========================================="

# 檢查遠程 route_photos 目錄是否存在
echo "檢查遠程 route_photos 目錄..."
REMOTE_PHOTOS_CHECK_CMD="[ -d '$REMOTE_ROUTE_PHOTOS' ] && [ -r '$REMOTE_ROUTE_PHOTOS' ]"
if ! ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_PHOTOS_CHECK_CMD"; then
    echo "⚠️  警告: 遠程 route_photos 目錄不存在或不可讀: $REMOTE_ROUTE_PHOTOS"
    echo "   跳過媒體庫同步"
else
    echo "✅ 遠程 route_photos 目錄存在且可讀"
    
    # 創建本地媒體庫目錄結構
    LOCAL_MEDIA="media"
    LOCAL_ROUTE_PHOTOS="$LOCAL_MEDIA/route_photos"
    mkdir -p "$LOCAL_ROUTE_PHOTOS"
    
    # 備份本地 route_photos（如果存在且不為空）
    if [ -d "$LOCAL_ROUTE_PHOTOS" ] && [ "$(ls -A $LOCAL_ROUTE_PHOTOS 2>/dev/null)" ]; then
        BACKUP_PHOTOS_DIR="$BACKUP_DIR/route_photos_backup_$(date +%Y%m%d_%H%M%S)"
        echo "備份本地 route_photos 到: $BACKUP_PHOTOS_DIR"
        cp -r "$LOCAL_ROUTE_PHOTOS" "$BACKUP_PHOTOS_DIR" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✅ 本地 route_photos 已備份"
        fi
    fi
    
    # 同步 route_photos
    echo ""
    echo "同步 route_photos..."
    echo "   從: $EC2_USER@$EC2_HOST:$REMOTE_ROUTE_PHOTOS/"
    echo "   到: $LOCAL_ROUTE_PHOTOS/"
    
    if [ "$USE_RSYNC" = true ]; then
        # 使用 rsync（支持增量同步，更高效，帶進度顯示）
        echo "   使用 rsync 同步（顯示進度）..."
        
        # 先獲取遠程目錄的總大小和文件數量（用於顯示總體進度）
        echo "   正在計算需要同步的文件..."
        REMOTE_TOTAL_SIZE_CMD="du -sb '$REMOTE_ROUTE_PHOTOS' 2>/dev/null | cut -f1"
        REMOTE_TOTAL_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_TOTAL_SIZE_CMD" 2>/dev/null || echo "0")
        REMOTE_FILE_COUNT_CMD="find '$REMOTE_ROUTE_PHOTOS' -type f 2>/dev/null | wc -l"
        REMOTE_FILE_COUNT=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_FILE_COUNT_CMD" 2>/dev/null || echo "0")
        
        if [ "$REMOTE_TOTAL_SIZE" -gt 0 ] 2>/dev/null && [ "$REMOTE_FILE_COUNT" -gt 0 ] 2>/dev/null; then
            REMOTE_SIZE_MB=$((REMOTE_TOTAL_SIZE / 1024 / 1024))
            echo "   總文件數: $REMOTE_FILE_COUNT"
            echo "   總大小: ${REMOTE_SIZE_MB} MB"
            echo ""
        fi
        
        # 執行 rsync 並顯示進度
        # 注意：源路徑帶 / 表示同步目錄內容，目標路徑不帶 / 表示同步到該目錄
        CURRENT_SIZE=0
        CURRENT_FILE=0
        rsync -avz --progress --delete \
            -e "ssh -i $EC2_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
            "$EC2_USER@$EC2_HOST:$REMOTE_ROUTE_PHOTOS/" \
            "$LOCAL_ROUTE_PHOTOS" 2>&1 | \
            while IFS= read -r line; do
                # 顯示文件傳輸進度
                if [[ "$line" =~ ^[a-zA-Z0-9_/.-]+[[:space:]]+[0-9]+%[[:space:]]+[0-9]+\.[0-9]+[KMGT]?B/s ]]; then
                    # 文件級別的進度
                    echo "   $line"
                elif [[ "$line" =~ ^[0-9]+/[0-9]+[[:space:]]+[0-9]+% ]] || [[ "$line" =~ ^[0-9]+% ]]; then
                    # 百分比進度
                    echo "   $line"
                elif [[ "$line" =~ ^[0-9]+\.[0-9]+[KMGT]?B/s ]]; then
                    # 速度信息
                    echo "   速度: $line"
                elif [[ "$line" =~ ^[a-zA-Z] ]] && [[ ! "$line" =~ ^(sending|receiving|building|deleting) ]]; then
                    # 文件名信息
                    echo "   $line"
                fi
            done
        SYNC_EXIT_CODE=${PIPESTATUS[0]}
        RSYNC_OUTPUT=""
        
        if [ $SYNC_EXIT_CODE -eq 0 ]; then
            echo ""
            echo "✅ route_photos 同步成功！"
            # 統計同步的文件數量
            FILE_COUNT=$(find "$LOCAL_ROUTE_PHOTOS" -type f 2>/dev/null | wc -l | tr -d ' ')
            echo "   文件數量: $FILE_COUNT"
            
            # 計算總大小
            if command -v du &> /dev/null; then
                TOTAL_SIZE=$(du -sh "$LOCAL_ROUTE_PHOTOS" 2>/dev/null | cut -f1)
                echo "   總大小: $TOTAL_SIZE"
            fi
        else
            echo ""
            echo "❌ route_photos 同步失敗，退出代碼: $SYNC_EXIT_CODE"
            if [ -n "$RSYNC_OUTPUT" ]; then
                echo "   RSYNC 錯誤輸出:"
                echo "$RSYNC_OUTPUT" | sed 's/^/   /'
            fi
        fi
    else
        # 使用 scp（備用方案，添加進度顯示）
        echo "   使用 scp 同步（顯示進度）..."
        
        # 先獲取遠程文件列表和總大小
        echo "   正在獲取文件列表..."
        REMOTE_FILES_CMD="find '$REMOTE_ROUTE_PHOTOS' -type f 2>/dev/null"
        REMOTE_FILE_LIST=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$REMOTE_FILES_CMD" 2>/dev/null)
        
        if [ -z "$REMOTE_FILE_LIST" ]; then
            echo "   ⚠️  警告: 遠程目錄為空或無法讀取文件列表"
            SYNC_EXIT_CODE=1
        else
            # 計算總文件數和總大小
            REMOTE_FILE_COUNT=$(echo "$REMOTE_FILE_LIST" | wc -l | tr -d ' ')
            REMOTE_TOTAL_SIZE=0
            
            # 計算總大小
            while IFS= read -r file; do
                [ -z "$file" ] && continue
                SIZE_CMD="stat -c%s '$file' 2>/dev/null || stat -f%z '$file' 2>/dev/null || echo '0'"
                FILE_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$SIZE_CMD" 2>/dev/null || echo "0")
                REMOTE_TOTAL_SIZE=$((REMOTE_TOTAL_SIZE + FILE_SIZE))
            done <<< "$REMOTE_FILE_LIST"
            
            if [ "$REMOTE_TOTAL_SIZE" -gt 0 ] 2>/dev/null && [ "$REMOTE_FILE_COUNT" -gt 0 ] 2>/dev/null; then
                REMOTE_SIZE_MB=$((REMOTE_TOTAL_SIZE / 1024 / 1024))
                echo "   總文件數: $REMOTE_FILE_COUNT"
                echo "   總大小: ${REMOTE_SIZE_MB} MB"
                echo ""
            fi
            
            # 逐個文件下載並顯示進度
            CURRENT_FILE=0
            CURRENT_SIZE=0
            SYNC_EXIT_CODE=0
            
            while IFS= read -r remote_file; do
                [ -z "$remote_file" ] && continue
                
                CURRENT_FILE=$((CURRENT_FILE + 1))
                
                # 計算相對路徑（移除遠程路徑前綴）
                # 處理可能的尾隨斜杠
                REMOTE_PREFIX="${REMOTE_ROUTE_PHOTOS%/}"
                RELATIVE_PATH="${remote_file#$REMOTE_PREFIX/}"
                # 如果移除前綴後路徑未改變，說明路徑不匹配，使用文件名
                if [ "$RELATIVE_PATH" = "$remote_file" ]; then
                    RELATIVE_PATH=$(basename "$remote_file")
                fi
                LOCAL_FILE="$LOCAL_ROUTE_PHOTOS/$RELATIVE_PATH"
                LOCAL_DIR=$(dirname "$LOCAL_FILE")
                mkdir -p "$LOCAL_DIR"
                
                # 獲取文件大小
                SIZE_CMD="stat -c%s '$remote_file' 2>/dev/null || stat -f%z '$remote_file' 2>/dev/null || echo '0'"
                FILE_SIZE=$(ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "$SIZE_CMD" 2>/dev/null || echo "0")
                
                # 顯示文件名和進度
                FILE_NAME=$(basename "$remote_file")
                printf "   [%d/%d] %s" "$CURRENT_FILE" "$REMOTE_FILE_COUNT" "$FILE_NAME"
                
                # 下載文件並顯示進度
                if command -v pv &> /dev/null && [ "$FILE_SIZE" != "0" ] && [ "$FILE_SIZE" -gt 0 ] 2>/dev/null; then
                    # 使用 pv 顯示進度條
                    ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$EC2_USER@$EC2_HOST" "cat '$remote_file'" 2>/dev/null | \
                        pv -s "$FILE_SIZE" -p -t -e -r -b > "$LOCAL_FILE" 2>&1
                    FILE_EXIT_CODE=$?
                else
                    # 使用 scp 下載（無進度條）
                    scp -i "$EC2_KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                        "$EC2_USER@$EC2_HOST:$remote_file" "$LOCAL_FILE" >/dev/null 2>&1
                    FILE_EXIT_CODE=$?
                fi
                
                if [ $FILE_EXIT_CODE -eq 0 ]; then
                    CURRENT_SIZE=$((CURRENT_SIZE + FILE_SIZE))
                    if [ "$REMOTE_TOTAL_SIZE" -gt 0 ] 2>/dev/null; then
                        PERCENT=$((CURRENT_SIZE * 100 / REMOTE_TOTAL_SIZE))
                        if [ $PERCENT -gt 100 ]; then
                            PERCENT=100
                        fi
                        FILE_SIZE_KB=$((FILE_SIZE / 1024))
                        printf " - %d KB - 總進度: %d%%\n" "$FILE_SIZE_KB" "$PERCENT"
                    else
                        FILE_SIZE_KB=$((FILE_SIZE / 1024))
                        printf " - %d KB\n" "$FILE_SIZE_KB"
                    fi
                else
                    echo " - ❌ 下載失敗"
                    SYNC_EXIT_CODE=1
                fi
            done <<< "$REMOTE_FILE_LIST"
        fi
        
        if [ $SYNC_EXIT_CODE -eq 0 ]; then
            echo ""
            echo "✅ route_photos 同步成功！"
            # 統計同步的文件數量
            FILE_COUNT=$(find "$LOCAL_ROUTE_PHOTOS" -type f 2>/dev/null | wc -l | tr -d ' ')
            echo "   文件數量: $FILE_COUNT"
            
            # 計算總大小
            if command -v du &> /dev/null; then
                TOTAL_SIZE=$(du -sh "$LOCAL_ROUTE_PHOTOS" 2>/dev/null | cut -f1)
                echo "   總大小: $TOTAL_SIZE"
            fi
        else
            echo ""
            echo "❌ route_photos 同步失敗，退出代碼: $SYNC_EXIT_CODE"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "同步完成！"
echo "=========================================="
