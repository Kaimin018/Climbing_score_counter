@echo off
chcp 65001 >nul
echo ========================================
echo 攀岩計分系統 - 自動啟動腳本
echo ========================================
echo.

REM 檢查是否在 Git 倉庫中
if exist .git (
    echo [0/3] 獲取最新代碼...
    git pull origin main
    if errorlevel 1 (
        echo 警告：獲取最新代碼失敗，將繼續使用本地代碼。
    ) else (
        echo 已獲取最新代碼
    )
    echo.
)

echo [1/3] 運行數據庫遷移...
python manage.py migrate
if errorlevel 1 (
    echo 遷移失敗！請檢查錯誤信息。
    pause
    exit /b 1
)
echo.

echo [2/3] 啟動開發服務器...
echo.
echo ========================================
echo 服務器將在 http://127.0.0.1:8000 啟動
echo ========================================
echo.
python manage.py runserver







