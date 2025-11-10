#!/bin/bash
# 檢查本地數據庫和媒體文件
# 使用方法：bash Deployment/scripts/tools/check_local_data.sh

# 獲取腳本目錄和項目根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT" || {
    echo "❌ 錯誤: 無法切換到項目根目錄: $PROJECT_ROOT"
    exit 1
}

echo "=========================================="
echo "檢查本地數據庫和媒體文件"
echo "=========================================="
echo ""

# 檢查 Python 命令
if [ -d "venv" ]; then
    if [ -f "venv/bin/python" ]; then
        PYTHON_CMD="venv/bin/python"
    elif [ -f "venv/Scripts/python.exe" ]; then
        PYTHON_CMD="venv/Scripts/python.exe"
    elif [ -f "venv/Scripts/python" ]; then
        PYTHON_CMD="venv/Scripts/python"
    else
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        elif command -v python &> /dev/null; then
            PYTHON_CMD="python"
        else
            echo "❌ 錯誤: 未找到 Python 命令"
            exit 1
        fi
    fi
else
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ 錯誤: 未找到 Python 命令"
        exit 1
    fi
fi

# 1. 檢查數據庫文件
echo "1. 檢查數據庫文件..."
if [ -f "db.sqlite3" ]; then
    DB_SIZE=$(stat -f%z "db.sqlite3" 2>/dev/null || stat -c%s "db.sqlite3" 2>/dev/null || echo "0")
    echo "   ✅ 數據庫文件存在"
    echo "   文件大小: $((DB_SIZE / 1024)) KB"
    
    # 檢查數據庫是否有效
    if $PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); conn.execute('SELECT 1'); conn.close()" 2>/dev/null; then
        echo "   ✅ 數據庫文件有效"
        
        # 檢查表數量
        TABLE_COUNT=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='table'\"); print(cursor.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
        echo "   表數量: $TABLE_COUNT"
        
        # 檢查是否有數據
        if [ "$TABLE_COUNT" -gt 0 ]; then
            echo ""
            echo "   檢查數據表內容..."
            
            # 檢查 scoring_room 表
            ROOM_COUNT=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='scoring_room'\"); exists = cursor.fetchone()[0]; print(exists); conn.close()" 2>/dev/null || echo "0")
            if [ "$ROOM_COUNT" -gt 0 ]; then
                ROOMS=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM scoring_room'); print(cursor.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
                echo "   - scoring_room: $ROOMS 個房間"
            fi
            
            # 檢查 scoring_route 表
            ROUTE_COUNT=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='scoring_route'\"); exists = cursor.fetchone()[0]; print(exists); conn.close()" 2>/dev/null || echo "0")
            if [ "$ROUTE_COUNT" -gt 0 ]; then
                ROUTES=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM scoring_route'); print(cursor.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
                echo "   - scoring_route: $ROUTES 個路線"
            fi
            
            # 檢查 scoring_climber 表
            CLIMBER_COUNT=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute(\"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='scoring_climber'\"); exists = cursor.fetchone()[0]; print(exists); conn.close()" 2>/dev/null || echo "0")
            if [ "$CLIMBER_COUNT" -gt 0 ]; then
                CLIMBERS=$($PYTHON_CMD -c "import sqlite3; conn = sqlite3.connect('db.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM scoring_climber'); print(cursor.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
                echo "   - scoring_climber: $CLIMBERS 個攀岩者"
            fi
        fi
    else
        echo "   ❌ 數據庫文件損壞或無效"
    fi
else
    echo "   ❌ 數據庫文件不存在"
fi

echo ""

# 2. 檢查媒體文件
echo "2. 檢查媒體文件..."
if [ -d "media" ]; then
    MEDIA_COUNT=$(find media -type f 2>/dev/null | wc -l | tr -d ' ')
    MEDIA_DIRS=$(find media -type d 2>/dev/null | wc -l | tr -d ' ')
    echo "   ✅ 媒體目錄存在"
    echo "   文件數量: $MEDIA_COUNT"
    echo "   目錄數量: $MEDIA_DIRS"
    
    if [ "$MEDIA_COUNT" -gt 0 ]; then
        if command -v du &> /dev/null; then
            MEDIA_SIZE=$(du -sh media 2>/dev/null | cut -f1)
            echo "   總大小: $MEDIA_SIZE"
        fi
        
        # 檢查 route_photos 目錄
        if [ -d "media/route_photos" ]; then
            PHOTO_COUNT=$(find media/route_photos -type f 2>/dev/null | wc -l | tr -d ' ')
            echo "   - route_photos: $PHOTO_COUNT 個照片"
            
            # 顯示前幾個文件
            if [ "$PHOTO_COUNT" -gt 0 ]; then
                echo "   示例文件:"
                find media/route_photos -type f 2>/dev/null | head -3 | while read -r file; do
                    echo "     - $file"
                done
            fi
        else
            echo "   ⚠️  route_photos 目錄不存在"
        fi
    else
        echo "   ⚠️  媒體目錄為空"
    fi
else
    echo "   ❌ 媒體目錄不存在"
fi

echo ""

# 3. 檢查 Django 配置
echo "3. 檢查 Django 配置..."
if $PYTHON_CMD manage.py check --deploy >/dev/null 2>&1; then
    echo "   ✅ Django 配置檢查通過"
    
    # 檢查 MEDIA_ROOT 和 MEDIA_URL
    MEDIA_ROOT=$($PYTHON_CMD -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climbing_system.settings'); import django; django.setup(); from django.conf import settings; print(settings.MEDIA_ROOT)" 2>/dev/null || echo "")
    MEDIA_URL=$($PYTHON_CMD -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climbing_system.settings'); import django; django.setup(); from django.conf import settings; print(settings.MEDIA_URL)" 2>/dev/null || echo "")
    
    if [ -n "$MEDIA_ROOT" ]; then
        echo "   MEDIA_ROOT: $MEDIA_ROOT"
        if [ -d "$MEDIA_ROOT" ]; then
            echo "   ✅ MEDIA_ROOT 目錄存在"
        else
            echo "   ⚠️  MEDIA_ROOT 目錄不存在"
        fi
    fi
    
    if [ -n "$MEDIA_URL" ]; then
        echo "   MEDIA_URL: $MEDIA_URL"
    fi
else
    echo "   ⚠️  Django 配置檢查失敗"
fi

echo ""
echo "=========================================="
echo "檢查完成"
echo "=========================================="

