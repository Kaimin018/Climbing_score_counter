#!/bin/bash

echo "========================================"
echo "攀岩計分系統 - 自動啟動腳本"
echo "========================================"
echo ""

echo "[1/2] 運行數據庫遷移..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "遷移失敗！請檢查錯誤信息。"
    exit 1
fi
echo ""

echo "[2/2] 啟動開發服務器..."
echo ""
echo "========================================"
echo "服務器將在 http://127.0.0.1:8000 啟動"
echo "========================================"
echo ""
python manage.py runserver







