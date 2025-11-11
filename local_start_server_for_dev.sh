#!/bin/bash

echo "========================================"
echo "攀岩計分系統 - 本地開發啟動腳本"
echo "========================================"
echo ""

# ============================================
# 檢查 Python 依賴（requirements.txt）
# ============================================
echo "[0/4] 檢查 Python 依賴..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤: 未找到 requirements.txt 文件"
    echo "   請確保在項目根目錄運行此腳本"
    exit 1
fi

# 檢查是否在虛擬環境中，優先使用虛擬環境的 Python（用於檢查依賴）
if [ -d "venv" ]; then
    if [ -f "venv/bin/python" ]; then
        CHECK_PYTHON_CMD="venv/bin/python"
    elif [ -f "venv/Scripts/python.exe" ]; then
        CHECK_PYTHON_CMD="venv/Scripts/python.exe"
    elif [ -f "venv/Scripts/python" ]; then
        CHECK_PYTHON_CMD="venv/Scripts/python"
    else
        if command -v python3 &> /dev/null; then
            CHECK_PYTHON_CMD="python3"
        elif command -v python &> /dev/null; then
            CHECK_PYTHON_CMD="python"
        else
            echo "❌ 錯誤: 未找到 Python 命令"
            exit 1
        fi
    fi
else
    if command -v python3 &> /dev/null; then
        CHECK_PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        CHECK_PYTHON_CMD="python"
    else
        echo "❌ 錯誤: 未找到 Python 命令"
        exit 1
    fi
fi

# 檢查 pip 是否可用
if ! $CHECK_PYTHON_CMD -m pip --version &> /dev/null; then
    echo "❌ 錯誤: pip 未安裝或不可用"
    echo "   請先安裝 pip: $CHECK_PYTHON_CMD -m ensurepip --upgrade"
    exit 1
fi

# 檢查關鍵依賴是否已安裝
echo "   檢查關鍵依賴..."
MISSING_DEPS=()
if ! $CHECK_PYTHON_CMD -c "import django" &> /dev/null; then
    MISSING_DEPS+=("Django")
fi
if ! $CHECK_PYTHON_CMD -c "import rest_framework" &> /dev/null; then
    MISSING_DEPS+=("djangorestframework")
fi
if ! $CHECK_PYTHON_CMD -c "import PIL" &> /dev/null; then
    MISSING_DEPS+=("Pillow")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "   ⚠️  警告: 以下依賴未安裝: ${MISSING_DEPS[*]}"
    echo "   正在安裝 requirements.txt 中的依賴..."
    $CHECK_PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "   ❌ 依賴安裝失敗，請手動執行: $CHECK_PYTHON_CMD -m pip install -r requirements.txt"
        exit 1
    fi
    echo "   ✅ 依賴安裝完成"
else
    echo "   ✅ 關鍵依賴已安裝"
fi
echo ""

# ============================================
# 數據庫和媒體庫同步配置說明
# ============================================
# 如果需要在啟動前自動從服務器同步數據庫和媒體庫，請配置：
# 
# 配置文件位置: security/EC2_security_config
# 
# 配置格式（每行一個配置項，支持註釋）:
#   EC2_HOST=your-ec2-ip-address                             # 遠端伺服器的 IP 地址/域名
#   EC2_KEY=security/your-key-file.pem                       # 遠端伺服器的 SSH 私鑰文件路徑（相對或絕對路徑）
#   EC2_USER=ubuntu                                          # 遠端伺服器的 SSH 用戶名（通常是 ubuntu）
#   DB_FILE_PATH="/var/www/Climbing_score_counter/db.sqlite3"  # 遠端伺服器的數據庫文件路徑（可選引號）
#   MEDIA_DIR_PATH="/var/www/Climbing_score_counter/media"    # 遠端伺服器的媒體庫目錄路徑（可選引號，默認值如上）
# 
# 注意：
#   - 如果未配置或配置文件不存在，將跳過數據庫和媒體庫同步步驟
#   - 數據庫同步失敗不會阻止啟動，會使用本地數據庫
#   - 媒體庫同步失敗不會阻止啟動，會使用本地媒體庫
#   - 媒體庫同步會自動備份本地媒體庫（如果存在）
#   - 如果系統安裝了 rsync，將使用 rsync 進行增量同步（更高效）；否則使用 scp
#   - 配置文件包含敏感信息，不應提交到版本控制系統
# ============================================

# 檢查是否在虛擬環境中，優先使用虛擬環境的 Python
if [ -d "venv" ]; then
    # 檢測操作系統類型，使用對應的 Python 可執行文件
    if [ -f "venv/bin/python" ]; then
        # Linux/macOS 或 Git Bash (Unix 風格)
        PYTHON_CMD="venv/bin/python"
        echo "ℹ️  檢測到虛擬環境，使用虛擬環境的 Python: $PYTHON_CMD"
        # 嘗試激活虛擬環境（設置環境變數）
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi
        echo ""
    elif [ -f "venv/Scripts/python.exe" ]; then
        # Windows (直接使用 Python 可執行文件，避免激活腳本問題)
        PYTHON_CMD="venv/Scripts/python.exe"
        echo "ℹ️  檢測到 Windows 虛擬環境，使用: $PYTHON_CMD"
        echo ""
    elif [ -f "venv/Scripts/python" ]; then
        # Windows (Git Bash 路徑格式)
        PYTHON_CMD="venv/Scripts/python"
        echo "ℹ️  檢測到 Windows 虛擬環境，使用: $PYTHON_CMD"
        echo ""
    else
        # 虛擬環境存在但找不到 Python，使用系統 Python
        echo "⚠️  警告: 找到 venv 目錄，但未找到 Python 可執行文件"
        echo "   將使用系統 Python"
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v python &> /dev/null; then
            PYTHON_CMD="python"
        else
            echo "❌ 錯誤: 未找到 Python 命令"
            echo "   請確保已安裝 Python 3.8+ 並在 PATH 中"
            exit 1
        fi
        echo ""
    fi
else
    # 沒有虛擬環境，使用系統 Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ 錯誤: 未找到 Python 命令"
        echo "   請確保已安裝 Python 3.8+ 並在 PATH 中"
        exit 1
    fi
fi

# 從服務器同步數據庫和媒體庫（如果配置了）
echo "[1/4] 同步數據庫和媒體庫..."
# 提示：如果需要強制同步媒體庫，可以設置環境變數 FORCE_MEDIA_SYNC=1
# 例如：FORCE_MEDIA_SYNC=1 bash local_start_server_for_dev.sh
if [ -f "security/EC2_security_config" ]; then
    # 檢查同步腳本是否存在
    if [ -f "Deployment/scripts/tools/sync_db_from_server.sh" ]; then
        # 記錄同步前的數據庫文件大小（如果存在）
        if [ -f "db.sqlite3" ]; then
            OLD_DB_SIZE=$(stat -f%z "db.sqlite3" 2>/dev/null || stat -c%s "db.sqlite3" 2>/dev/null || echo "0")
        else
            OLD_DB_SIZE="0"
        fi
        
        # 執行同步腳本（直接輸出，不捕獲）
        # 傳遞 FORCE_MEDIA_SYNC 環境變數（如果設置了）
        if [ -n "$FORCE_MEDIA_SYNC" ]; then
            export FORCE_MEDIA_SYNC
            echo "   ℹ️  強制同步媒體庫模式已啟用"
        fi
        bash "Deployment/scripts/tools/sync_db_from_server.sh"
        SYNC_EXIT_CODE=$?
        
        # 只有在同步成功時才檢查數據庫文件更新情況
        if [ $SYNC_EXIT_CODE -eq 0 ]; then
            # 檢查數據庫文件是否真的被更新了（使用文件大小而不是時間戳，更可靠）
            if [ -f "db.sqlite3" ]; then
                NEW_DB_SIZE=$(stat -f%z "db.sqlite3" 2>/dev/null || stat -c%s "db.sqlite3" 2>/dev/null || echo "0")
                if [ "$NEW_DB_SIZE" != "$OLD_DB_SIZE" ] && [ "$OLD_DB_SIZE" != "0" ]; then
                    echo "   ℹ️  數據庫文件已更新（文件大小改變：${OLD_DB_SIZE} → ${NEW_DB_SIZE} 字節）"
                elif [ "$OLD_DB_SIZE" = "0" ] && [ -f "db.sqlite3" ] && [ "$NEW_DB_SIZE" -gt 0 ] 2>/dev/null; then
                    echo "   ℹ️  數據庫文件已創建（大小：${NEW_DB_SIZE} 字節）"
                elif [ "$NEW_DB_SIZE" -gt 0 ] 2>/dev/null; then
                    # 文件大小相同但大于0，可能是远程文件没有变化，这是正常的
                    echo "   ℹ️  數據庫文件已同步（與遠程一致，大小：${NEW_DB_SIZE} 字節）"
                else
                    echo "   ⚠️  警告：數據庫文件大小為 0，可能下載失敗"
                fi
            fi
        fi
    else
        echo "⚠️  警告：同步腳本不存在: Deployment/scripts/tools/sync_db_from_server.sh"
        SYNC_EXIT_CODE=1
    fi
    
    if [ $SYNC_EXIT_CODE -ne 0 ]; then
        echo "⚠️  警告：數據庫和媒體庫同步失敗，將使用本地數據庫和媒體庫。"
    else
        echo "✅ 數據庫和媒體庫同步成功"
        # 驗證下載的數據庫文件是否有效
        if [ -f "db.sqlite3" ]; then
            echo "   驗證數據庫文件..."
            if $PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); conn.execute('SELECT 1'); conn.close()" 2>/dev/null; then
                echo "   ✅ 數據庫文件有效"
            else
                echo "   ❌ 數據庫文件損壞或無效"
                echo "   正在從備份恢復..."
                # 查找最新的備份文件夾（統一備份格式）
                LATEST_BACKUP_DIR=$(ls -td backups/local_backup_* 2>/dev/null | head -1)
                if [ -n "$LATEST_BACKUP_DIR" ] && [ -d "$LATEST_BACKUP_DIR" ] && [ -f "$LATEST_BACKUP_DIR/db.sqlite3" ]; then
                    cp "$LATEST_BACKUP_DIR/db.sqlite3" "db.sqlite3"
                    echo "   ✅ 已從備份恢復: $LATEST_BACKUP_DIR/db.sqlite3"
                else
                    echo "   ⚠️  未找到備份文件，將刪除損壞的數據庫文件"
                    rm -f "db.sqlite3"
                    echo "   ℹ️  數據庫將在遷移時重新創建"
                fi
            fi
        fi
    fi
else
    echo "ℹ️  未找到配置文件 security/EC2_security_config，跳過數據庫和媒體庫同步"
    # 即使不同步，也檢查現有數據庫文件是否有效
    if [ -f "db.sqlite3" ]; then
        echo "   檢查本地數據庫文件..."
        if ! $PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); conn.execute('SELECT 1'); conn.close()" 2>/dev/null; then
            echo "   ❌ 本地數據庫文件損壞"
            echo "   正在從備份恢復..."
            # 查找最新的備份文件夾（統一備份格式）
            LATEST_BACKUP_DIR=$(ls -td backups/local_backup_* 2>/dev/null | head -1)
            if [ -n "$LATEST_BACKUP_DIR" ] && [ -d "$LATEST_BACKUP_DIR" ] && [ -f "$LATEST_BACKUP_DIR/db.sqlite3" ]; then
                cp "$LATEST_BACKUP_DIR/db.sqlite3" "db.sqlite3"
                echo "   ✅ 已從備份恢復: $LATEST_BACKUP_DIR/db.sqlite3"
            else
                echo "   ⚠️  未找到備份文件，將刪除損壞的數據庫文件"
                rm -f "db.sqlite3"
                echo "   ℹ️  數據庫將在遷移時重新創建"
            fi
        else
            echo "   ✅ 本地數據庫文件有效"
        fi
    fi
fi
echo ""

echo "[2/4] 運行數據庫遷移..."
$PYTHON_CMD manage.py migrate
if [ $? -ne 0 ]; then
    echo "遷移失敗！請檢查錯誤信息。"
    exit 1
fi
echo ""

# 檢查數據庫中的數據
echo "檢查數據庫內容..."
ROOM_COUNT=$($PYTHON_CMD manage.py shell -c "from scoring.models import Room; print(Room.objects.count())" 2>/dev/null || echo "0")
ROUTE_COUNT=$($PYTHON_CMD manage.py shell -c "from scoring.models import Route; print(Route.objects.count())" 2>/dev/null || echo "0")
MEMBER_COUNT=$($PYTHON_CMD manage.py shell -c "from scoring.models import Member; print(Member.objects.count())" 2>/dev/null || echo "0")

if [ "$ROOM_COUNT" != "0" ] || [ "$ROUTE_COUNT" != "0" ] || [ "$MEMBER_COUNT" != "0" ]; then
    echo "   ✅ 數據庫中有數據："
    echo "      房間: $ROOM_COUNT"
    echo "      路線: $ROUTE_COUNT"
    echo "      成員: $MEMBER_COUNT"
else
    echo "   ⚠️  警告: 數據庫中沒有數據"
    echo "      如果剛從服務器同步，請檢查同步是否成功"
fi

# 檢查媒體文件
if [ -d "media" ]; then
    MEDIA_COUNT=$(find media -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MEDIA_COUNT" -gt 0 ]; then
        echo "   ✅ 媒體文件: $MEDIA_COUNT 個文件"
    else
        echo "   ⚠️  警告: 媒體目錄為空"
    fi
else
    echo "   ⚠️  警告: 媒體目錄不存在"
fi
echo ""

echo "[3/4] 啟動開發服務器..."
echo ""
echo "========================================"
echo "服務器將在 http://127.0.0.1:8000 啟動"
echo "========================================"
echo ""
$PYTHON_CMD manage.py runserver