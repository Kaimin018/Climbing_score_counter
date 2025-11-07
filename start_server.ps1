# Set PowerShell output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Climbing Score System - Auto Start Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in a Git repository
if (Test-Path .git) {
    Write-Host "[0/3] Fetching latest code..." -ForegroundColor Yellow
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to fetch latest code, will continue with local code." -ForegroundColor Yellow
    } else {
        Write-Host "Latest code fetched successfully" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "[1/3] Running database migrations..." -ForegroundColor Yellow
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "Migration failed! Please check the error messages." -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

Write-Host "[2/3] Starting development server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Server will start at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
python manage.py runserver







