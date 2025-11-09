#!/bin/bash

echo "========================================"
echo "攀岩計分系統 - 本地開發啟動腳本"
echo "========================================"
echo ""

# ============================================
# 數據庫同步配置說明
# ============================================
# 如果需要在啟動前自動從服務器同步數據庫，請配置：
# 
# 配置文件位置: security/EC2_security_config
# 
# 配置格式（每行一個配置項，支持註釋）:
#   EC2_HOST=your-ec2-ip-address                             # 遠端伺服器的 IP 地址/域名
#   EC2_KEY=security/your-key-file.pem                       # 遠端伺服器的 SSH 私鑰文件路徑（相對或絕對路徑）
#   EC2_USER=ubuntu                                          # 遠端伺服器的 SSH 用戶名（通常是 ubuntu）
#   DB_FILE_PATH="/var/www/Climbing_score_counter/db.sqlite3"  # 遠端伺服器的數據庫文件路徑（可選引號）
# 
# 注意：
#   - 如果未配置或配置文件不存在，將跳過數據庫同步步驟
#   - 數據庫同步失敗不會阻止啟動，會使用本地數據庫
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

# 從服務器同步數據庫（如果配置了）
echo "[1/3] 同步數據庫..."
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
        bash "Deployment/scripts/tools/sync_db_from_server.sh"
        SYNC_EXIT_CODE=$?
        
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
    else
        echo "⚠️  警告：同步腳本不存在: Deployment/scripts/tools/sync_db_from_server.sh"
        SYNC_EXIT_CODE=1
    fi
    
    if [ $SYNC_EXIT_CODE -ne 0 ]; then
        echo "⚠️  警告：數據庫同步失敗，將使用本地數據庫。"
    else
        echo "✅ 數據庫同步成功"
        # 驗證下載的數據庫文件是否有效
        if [ -f "db.sqlite3" ]; then
            echo "   驗證數據庫文件..."
            if $PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); conn.execute('SELECT 1'); conn.close()" 2>/dev/null; then
                echo "   ✅ 數據庫文件有效"
            else
                echo "   ❌ 數據庫文件損壞或無效"
                echo "   正在從備份恢復..."
                # 查找最新的備份文件
                LATEST_BACKUP=$(ls -t backups/db_local_backup_*.sqlite3 2>/dev/null | head -1)
                if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
                    cp "$LATEST_BACKUP" "db.sqlite3"
                    echo "   ✅ 已從備份恢復: $LATEST_BACKUP"
                else
                    echo "   ⚠️  未找到備份文件，將刪除損壞的數據庫文件"
                    rm -f "db.sqlite3"
                    echo "   ℹ️  數據庫將在遷移時重新創建"
                fi
            fi
        fi
    fi
else
    echo "ℹ️  未找到配置文件 security/EC2_security_config，跳過數據庫同步"
    # 即使不同步，也檢查現有數據庫文件是否有效
    if [ -f "db.sqlite3" ]; then
        echo "   檢查本地數據庫文件..."
        if ! $PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); conn.execute('SELECT 1'); conn.close()" 2>/dev/null; then
            echo "   ❌ 本地數據庫文件損壞"
            echo "   正在從備份恢復..."
            LATEST_BACKUP=$(ls -t backups/db_local_backup_*.sqlite3 2>/dev/null | head -1)
            if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
                cp "$LATEST_BACKUP" "db.sqlite3"
                echo "   ✅ 已從備份恢復: $LATEST_BACKUP"
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

echo "[2/3] 運行數據庫遷移..."
$PYTHON_CMD manage.py migrate
if [ $? -ne 0 ]; then
    echo "遷移失敗！請檢查錯誤信息。"
    exit 1
fi
echo ""

echo "[3/3] 啟動開發服務器..."
echo ""
echo "========================================"
echo "服務器將在 http://127.0.0.1:8000 啟動"
echo "========================================"
echo ""
$PYTHON_CMD manage.py runserver