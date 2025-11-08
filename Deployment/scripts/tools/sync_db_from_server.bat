@echo off
setlocal enabledelayedexpansion
REM Windows batch script: Sync database from AWS EC2 to local
REM Usage: Double-click this file, or run from command line

REM Get script directory and navigate to project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo Syncing database from AWS EC2 to local
echo ==========================================
echo.

REM Import configuration from EC2_security_config file
set SECURITY_FILE=security\EC2_security_config
if not exist "%SECURITY_FILE%" (
    echo Error: Configuration file %SECURITY_FILE% not found
    pause
    exit /b 1
)

REM Read configuration (skip comment lines and empty lines)
REM Suppress findstr errors by redirecting stderr
for /f "tokens=1,2 delims==" %%a in ('findstr /v "^#" "%SECURITY_FILE%" 2^>nul ^| findstr /v "^$" 2^>nul') do (
    if "%%a"=="EC2_HOST" set EC2_HOST=%%b
    if "%%a"=="EC2_KEY" (
        set "TEMP_KEY=%%b"
        REM Expand environment variables: replace %USERPROFILE% in file with actual value (if present)
        set "EC2_KEY=!TEMP_KEY!"
        REM Check if path contains %USERPROFILE% using string replacement
        set "TEST_KEY=!TEMP_KEY!"
        set "TEST_KEY=!TEST_KEY:%%USERPROFILE%%=!"
        if not "!TEST_KEY!"=="!TEMP_KEY!" (
            REM Contains %USERPROFILE%, expand it
            call set "EC2_KEY=%%TEMP_KEY:%%USERPROFILE%%=%USERPROFILE%%%"
        )
        REM Convert relative path to absolute path based on project root
        REM Check if path is absolute (starts with drive letter like C: or D:)
        set "IS_ABSOLUTE=0"
        echo !EC2_KEY! | findstr /R /C:"^[A-Za-z]:" >nul
        if !ERRORLEVEL! EQU 0 set "IS_ABSOLUTE=1"
        REM Also check if it starts with backslash (absolute path from root)
        echo !EC2_KEY! | findstr /R /C:"^\\" >nul
        if !ERRORLEVEL! EQU 0 set "IS_ABSOLUTE=1"
        
        if !IS_ABSOLUTE! EQU 0 (
            REM It's a relative path, convert to absolute based on project root
            for %%F in ("!PROJECT_ROOT!\!EC2_KEY!") do (
                set "EC2_KEY=%%~fF"
            )
        ) else (
            REM It's already an absolute path, just normalize it
            for %%F in ("!EC2_KEY!") do (
                set "EC2_KEY=%%~fF"
            )
        )
    )
    if "%%a"=="EC2_USER" set EC2_USER=%%b
)

REM If configuration not found, use default values
if "%EC2_HOST%"=="" set EC2_HOST=3.26.6.19
if "!EC2_KEY!"=="" set EC2_KEY=%USERPROFILE%\.ssh\your-key.pem
if "%EC2_USER%"=="" set EC2_USER=ubuntu

REM Configuration
set PROJECT_DIR=/var/www/Climbing_score_counter
set REMOTE_DB=%PROJECT_DIR%/db.sqlite3
set LOCAL_DB=db.sqlite3
set BACKUP_DIR=backups

echo Configuration information:
echo   EC2_HOST: %EC2_HOST%
echo   EC2_KEY: !EC2_KEY!
echo   EC2_USER: %EC2_USER%
echo.

REM Check if key file exists
if not exist "!EC2_KEY!" (
    echo ❌ Error: Key file not found: !EC2_KEY!
    echo    Please ensure the key file exists or update the path in security\EC2_security_config
    pause
    exit /b 1
)

REM Check if OpenSSH is available
where ssh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error: OpenSSH client not found
    echo    Please install OpenSSH client:
    echo    1. Open Settings ^> Apps ^> Optional Features
    echo    2. Add feature ^> OpenSSH Client
    pause
    exit /b 1
)

REM Check SSH connection
echo Checking SSH connection...
ssh -i "!EC2_KEY!" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=nul "%EC2_USER%@%EC2_HOST%" "echo Connection successful" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Cannot connect to server %EC2_USER%@%EC2_HOST%
    echo    Please check:
    echo    1. EC2_HOST is correct: %EC2_HOST%
    echo    2. EC2_KEY path is correct: !EC2_KEY!
    echo    3. Key file exists: Yes
    echo    4. Network connection is normal
    echo    5. Key file matches the EC2 instance
    pause
    exit /b 1
)
echo ✅ SSH connection successful

REM Check if remote database exists
echo Checking remote database...
ssh -i "!EC2_KEY!" -o StrictHostKeyChecking=no -o UserKnownHostsFile=nul "%EC2_USER%@%EC2_HOST%" "test -f %REMOTE_DB%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Remote database does not exist: %REMOTE_DB%
    pause
    exit /b 1
)

REM Create local backup directory
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Backup local database if exists
if exist "%LOCAL_DB%" (
    REM Generate backup filename with timestamp
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do (
        set "YEAR=%%c"
        set "MONTH=%%a"
        set "DAY=%%b"
    )
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
        set "HOUR=%%a"
        set "MINUTE=%%b"
    )
    REM Pad with zeros
    if !MONTH! LSS 10 set "MONTH=0!MONTH!"
    if !DAY! LSS 10 set "DAY=0!DAY!"
    set "HOUR=!HOUR: =0!"
    set "MINUTE=!MINUTE: =0!"
    set "BACKUP_NAME=%BACKUP_DIR%\db_local_backup_!YEAR!!MONTH!!DAY!_!HOUR!!MINUTE!.sqlite3"
    echo Backing up local database to: !BACKUP_NAME!
    copy "%LOCAL_DB%" "!BACKUP_NAME!" >nul
    if !ERRORLEVEL! EQU 0 (
        echo ✅ Local database backed up
    ) else (
        echo ⚠️  Warning: Failed to backup local database
    )
) else (
    echo ℹ️  Local database does not exist, skipping backup
)

REM Download remote database
echo Downloading remote database...
scp -i "!EC2_KEY!" -o StrictHostKeyChecking=no -o UserKnownHostsFile=nul "%EC2_USER%@%EC2_HOST%:%REMOTE_DB%" "%LOCAL_DB%"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Database download failed
    pause
    exit /b 1
)

REM Check if download was successful
if exist "%LOCAL_DB%" (
    for %%A in ("%LOCAL_DB%") do set "FILE_SIZE=%%~zA"
    set /a FILE_SIZE_KB=!FILE_SIZE!/1024
    set /a FILE_SIZE_MB=!FILE_SIZE!/1024/1024
    if !FILE_SIZE_MB! GTR 0 (
        echo ✅ Database downloaded successfully!
        echo    File size: !FILE_SIZE_MB! MB
    ) else (
        echo ✅ Database downloaded successfully!
        echo    File size: !FILE_SIZE_KB! KB
    )
    echo    Location: %LOCAL_DB%
) else (
    echo ❌ Database download failed
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Sync completed!
echo ==========================================
echo.
echo ⚠️  Notes:
echo    1. Local database backed up to: %BACKUP_DIR%\
echo    2. If you encounter issues, you can restore from backup
echo    3. It's recommended to stop the local development server before syncing
echo.
pause

