#!/bin/bash
# 修復虛擬環境路徑問題
# 使用方法：bash fix_venv_path.sh

set -e

echo "========================================="
echo "修復虛擬環境路徑"
echo "========================================="

# 項目目錄
PROJECT_DIR="/var/www/Climbing_score_counter"
VENV_DIR="$PROJECT_DIR/venv"
OLD_VENV_DIR="/var/www/climbing_score_counting_system/venv"

# 檢查項目目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "錯誤: 項目目錄不存在: $PROJECT_DIR"
    exit 1
fi

# 進入項目目錄
cd $PROJECT_DIR || {
    echo "錯誤: 無法進入項目目錄: $PROJECT_DIR"
    exit 1
}

# 退出當前虛擬環境（如果已激活）
if [ -n "$VIRTUAL_ENV" ]; then
    echo "檢測到已激活的虛擬環境，正在退出..."
    deactivate 2>/dev/null || true
fi

# 檢查新路徑的虛擬環境是否存在
if [ -d "$VENV_DIR" ]; then
    echo "新路徑的虛擬環境已存在: $VENV_DIR"
    echo "正在驗證虛擬環境..."
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "✅ 虛擬環境正常"
        source $VENV_DIR/bin/activate
        echo "✅ 已激活正確的虛擬環境"
        echo "當前 Python 路徑: $(which python)"
        echo "當前 pip 路徑: $(which pip)"
    else
        echo "⚠️  虛擬環境不完整，正在重新創建..."
        rm -rf $VENV_DIR
        python3 -m venv $VENV_DIR
        source $VENV_DIR/bin/activate
        echo "✅ 虛擬環境重新創建完成"
    fi
else
    echo "新路徑的虛擬環境不存在，正在創建..."
    
    # 如果舊路徑的虛擬環境存在，可以選擇遷移或重新創建
    if [ -d "$OLD_VENV_DIR" ]; then
        echo "檢測到舊路徑的虛擬環境: $OLD_VENV_DIR"
        read -p "是否要遷移舊虛擬環境？(y/n): " migrate_choice
        if [ "$migrate_choice" = "y" ] || [ "$migrate_choice" = "Y" ]; then
            echo "正在遷移虛擬環境..."
            cp -r $OLD_VENV_DIR $VENV_DIR
            # 更新虛擬環境中的路徑引用
            echo "正在更新虛擬環境中的路徑引用..."
            find $VENV_DIR -type f -name "*.pyc" -delete
            find $VENV_DIR -type f -name "*.pyo" -delete
            find $VENV_DIR -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            # 重新生成激活腳本
            python3 -m venv --upgrade $VENV_DIR
            echo "✅ 虛擬環境遷移完成"
        else
            echo "正在創建新的虛擬環境..."
            python3 -m venv $VENV_DIR
            echo "✅ 虛擬環境創建完成"
        fi
    else
        echo "正在創建新的虛擬環境..."
        python3 -m venv $VENV_DIR
        echo "✅ 虛擬環境創建完成"
    fi
    
    source $VENV_DIR/bin/activate
fi

# 驗證虛擬環境
echo ""
echo "========================================="
echo "虛擬環境驗證"
echo "========================================="
echo "虛擬環境路徑: $VIRTUAL_ENV"
echo "Python 路徑: $(which python)"
echo "pip 路徑: $(which pip)"
echo "Python 版本: $(python --version)"
echo "pip 版本: $(pip --version)"

# 升級 pip
echo ""
echo "正在升級 pip..."
pip install --upgrade pip

echo ""
echo "========================================="
echo "修復完成！"
echo "========================================="
echo ""
echo "現在可以運行以下命令安裝依賴："
echo "  pip install -r requirements.txt"
echo ""
echo "或者運行部署腳本："
echo "  bash deploy.sh"
echo ""

