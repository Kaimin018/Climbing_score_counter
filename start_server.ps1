# 設置 PowerShell 輸出編碼為 UTF-8，解決中文亂碼問題
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "攀岩計分系統 - 自動啟動腳本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查是否在 Git 倉庫中
if (Test-Path .git) {
    Write-Host "[0/3] 獲取最新代碼..." -ForegroundColor Yellow
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "警告：獲取最新代碼失敗，將繼續使用本地代碼。" -ForegroundColor Yellow
    } else {
        Write-Host "已獲取最新代碼" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "[1/3] 運行數據庫遷移..." -ForegroundColor Yellow
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "遷移失敗！請檢查錯誤信息。" -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

Write-Host "[2/3] 啟動開發服務器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "服務器將在 http://127.0.0.1:8000 啟動" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
python manage.py runserver







