#!/bin/bash

echo "========================================"
echo "攀岩計分系統 - 自動啟動腳本"
echo "========================================"
echo ""

# 檢查是否在 Git 倉庫中
if [ -d .git ]; then
    echo "[0/3] 獲取最新代碼..."
    git pull origin main
    if [ $? -ne 0 ]; then
        echo "警告：獲取最新代碼失敗，將繼續使用本地代碼。"
    else
        echo "已獲取最新代碼"
    fi
    echo ""
fi

echo "[1/3] 運行數據庫遷移..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "遷移失敗！請檢查錯誤信息。"
    exit 1
fi
echo ""

echo "[2/3] 啟動開發服務器..."
echo ""
echo "========================================"
echo "服務器將在 http://127.0.0.1:8000 啟動"
echo "========================================"
echo ""
python manage.py runserver







