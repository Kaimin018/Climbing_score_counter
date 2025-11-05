Write-Host "========================================" -ForegroundColor Cyan
Write-Host "攀岩計分系統 - 自動啟動腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] 運行數據庫遷移..." -ForegroundColor Yellow
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "遷移失敗！請檢查錯誤信息。" -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

Write-Host "[2/3] 初始化默認數據..." -ForegroundColor Yellow
python manage.py init_default_data
if ($LASTEXITCODE -ne 0) {
    Write-Host "初始化失敗！請檢查錯誤信息。" -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

Write-Host "[3/3] 啟動開發服務器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "服務器將在 http://127.0.0.1:8000 啟動" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
python manage.py runserver







