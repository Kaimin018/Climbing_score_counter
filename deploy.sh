#!/bin/bash
# AWS EC2 部署腳本
# 使用方法：bash deploy.sh

set -e  # 遇到錯誤立即退出

echo "開始部署攀岩計分系統..."

# 項目目錄
PROJECT_DIR="/var/www/Climbing_score_counter"
VENV_DIR="$PROJECT_DIR/venv"

# 檢查項目目錄是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "錯誤: 項目目錄不存在: $PROJECT_DIR"
    echo "請先創建目錄或檢查路徑是否正確"
    exit 1
fi

# 進入項目目錄
cd $PROJECT_DIR || {
    echo "錯誤: 無法進入項目目錄: $PROJECT_DIR"
    exit 1
}

# 如果使用 Git，拉取最新代碼
if [ -d ".git" ]; then
    echo "拉取最新代碼..."
    git fetch origin
    git reset --hard origin/main || git reset --hard origin/master
    echo "代碼更新完成"
else
    echo "警告: 未檢測到 Git 倉庫，跳過代碼更新"
fi

# 激活虛擬環境
echo "激活虛擬環境..."
source $VENV_DIR/bin/activate

# 安裝/更新依賴
echo "安裝依賴..."
pip install --upgrade pip
pip install -r requirements.txt

# 運行數據庫遷移
echo "運行數據庫遷移..."
python manage.py migrate --noinput

# 收集靜態文件
echo "收集靜態文件..."
python manage.py collectstatic --noinput --clear

# 創建日誌目錄（如果不存在）
echo "創建日誌目錄..."
mkdir -p $PROJECT_DIR/logs
chown -R www-data:www-data $PROJECT_DIR/logs

# 設置文件權限
echo "設置文件權限..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
chmod -R 775 $PROJECT_DIR/media
chmod -R 775 $PROJECT_DIR/logs

# 重啟 Gunicorn 服務
echo "重啟 Gunicorn 服務..."
systemctl daemon-reload
systemctl restart climbing_system

# 檢查服務狀態
echo "檢查服務狀態..."
systemctl status climbing_system --no-pager

# 重載 Nginx（如果需要）
echo "重載 Nginx..."
nginx -t && systemctl reload nginx

echo "部署完成！"
echo "請檢查服務狀態："
echo "  - Gunicorn: sudo systemctl status climbing_system"
echo "  - Nginx: sudo systemctl status nginx"
echo "  - 日誌: tail -f $PROJECT_DIR/logs/gunicorn_error.log"

