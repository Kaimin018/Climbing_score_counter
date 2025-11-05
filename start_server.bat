@echo off
echo ========================================
echo 攀岩計分系統 - 自動啟動腳本
echo ========================================
echo.

echo [1/3] 運行數據庫遷移...
python manage.py migrate
if errorlevel 1 (
    echo 遷移失敗！請檢查錯誤信息。
    pause
    exit /b 1
)
echo.

echo [2/3] 初始化默認數據...
python manage.py init_default_data
if errorlevel 1 (
    echo 初始化失敗！請檢查錯誤信息。
    pause
    exit /b 1
)
echo.

echo [3/3] 啟動開發服務器...
echo.
echo ========================================
echo 服務器將在 http://127.0.0.1:8000 啟動
echo ========================================
echo.
python manage.py runserver







