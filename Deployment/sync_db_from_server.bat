@echo off
setlocal enabledelayedexpansion
REM Windows 批處理腳本：從 AWS EC2 同步數據庫到本地
REM 使用方法：雙擊此文件，或從命令行運行

echo ==========================================
echo 從 AWS EC2 同步數據庫到本地
echo ==========================================
echo.

REM 從 EC2_security_config 文件導入配置
set SECURITY_FILE=security\EC2_security_config
if not exist "%SECURITY_FILE%" (
    echo 錯誤: 找不到配置文件 %SECURITY_FILE%
    pause
    exit /b 1
)

REM 讀取配置（跳過註釋行和空行）
for /f "tokens=1,2 delims==" %%a in ('findstr /v "^#" "%SECURITY_FILE%" ^| findstr /v "^$"') do (
    if "%%a"=="EC2_HOST" set EC2_HOST=%%b
    if "%%a"=="EC2_KEY" (
        set "TEMP_KEY=%%b"
        REM 展開環境變數：將文件中的 %USERPROFILE% 替換為實際值
        call set "EC2_KEY=%%TEMP_KEY:%%USERPROFILE%%=%USERPROFILE%%%"
    )
    if "%%a"=="EC2_USER" set EC2_USER=%%b
)

REM 如果配置未找到，使用默認值
if "%EC2_HOST%"=="" set EC2_HOST=3.26.6.19
if "%EC2_KEY%"=="" set EC2_KEY=%USERPROFILE%\.ssh\your-key.pem
if "%EC2_USER%"=="" set EC2_USER=ubuntu

echo 配置信息:
echo   EC2_HOST: %EC2_HOST%
echo   EC2_KEY: %EC2_KEY%
echo   EC2_USER: %EC2_USER%
echo.

REM 檢查 Git Bash 是否存在
where bash >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 錯誤: 找不到 bash 命令
    echo 請確保已安裝 Git for Windows 或 WSL
    echo.
    echo 如果使用 WSL，請在 WSL 終端中運行：
    echo   export EC2_HOST=3.26.6.19
    echo   export EC2_KEY=~/.ssh/your-key.pem
    echo   bash Deployment/sync_database_from_server.sh
    pause
    exit /b 1
)

REM 使用 Git Bash 執行同步腳本
echo 正在執行同步腳本...
bash -c "export EC2_HOST=%EC2_HOST%; export EC2_KEY=%EC2_KEY%; export EC2_USER=%EC2_USER%; bash Deployment/sync_database_from_server.sh"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 同步完成！
) else (
    echo.
    echo ❌ 同步失敗，請檢查錯誤信息
)

echo.
pause

