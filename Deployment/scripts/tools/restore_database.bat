@echo off
setlocal enabledelayedexpansion
REM Windows batch script: Restore database from backup
REM Usage: Double-click this file, or run from command line

REM Get script directory and navigate to project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo Restore Database from Backup
echo ==========================================
echo.

set BACKUP_DIR=backups
set LOCAL_DB=db.sqlite3

REM Check if backup directory exists
if not exist "%BACKUP_DIR%" (
    echo ❌ Error: Backup directory not found: %BACKUP_DIR%
    pause
    exit /b 1
)

REM List available backups
echo Available backup files:
echo.
set /a COUNT=0
for %%F in ("%BACKUP_DIR%\db_local_backup_*.sqlite3") do (
    set /a COUNT+=1
    for %%A in ("%%F") do (
        set "BACKUP_FILE=%%~nxF"
        set "BACKUP_DATE=%%~tF"
        set "BACKUP_SIZE=%%~zA"
        set /a BACKUP_SIZE_KB=!BACKUP_SIZE!/1024
        echo   !COUNT!. !BACKUP_FILE!
        echo      Date: !BACKUP_DATE!
        echo      Size: !BACKUP_SIZE_KB! KB
        echo.
    )
)

if !COUNT! EQU 0 (
    echo ❌ No backup files found in %BACKUP_DIR%
    pause
    exit /b 1
)

REM Ask user to select backup
echo Please enter the backup number to restore (1-!COUNT!), or 'q' to quit:
set /p SELECTION="Selection: "

if /i "!SELECTION!"=="q" (
    echo Operation cancelled.
    pause
    exit /b 0
)

REM Validate selection
set /a SELECTION_NUM=!SELECTION! 2>nul
if !SELECTION_NUM! LSS 1 (
    echo ❌ Invalid selection
    pause
    exit /b 1
)
if !SELECTION_NUM! GTR !COUNT! (
    echo ❌ Invalid selection
    pause
    exit /b 1
)

REM Get the selected backup file
set /a CURRENT=0
for %%F in ("%BACKUP_DIR%\db_local_backup_*.sqlite3") do (
    set /a CURRENT+=1
    if !CURRENT! EQU !SELECTION_NUM! (
        set "SELECTED_BACKUP=%%F"
        goto :found
    )
)

:found
if not defined SELECTED_BACKUP (
    echo ❌ Error: Could not find selected backup
    pause
    exit /b 1
)

echo.
echo Selected backup: %SELECTED_BACKUP%
echo.

REM Confirm restore operation
echo ⚠️  WARNING: This will replace the current database with the backup!
echo    Current database: %LOCAL_DB%
echo    Backup file: %SELECTED_BACKUP%
echo.
set /p CONFIRM="Are you sure you want to restore? (yes/no): "

if /i not "!CONFIRM!"=="yes" (
    echo Operation cancelled.
    pause
    exit /b 0
)

REM Backup current database before restore (if exists)
if exist "%LOCAL_DB%" (
    echo.
    echo Creating backup of current database before restore...
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do (
        set "YEAR=%%c"
        set "MONTH=%%a"
        set "DAY=%%b"
    )
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
        set "HOUR=%%a"
        set "MINUTE=%%b"
    )
    if !MONTH! LSS 10 set "MONTH=0!MONTH!"
    if !DAY! LSS 10 set "DAY=0!DAY!"
    set "HOUR=!HOUR: =0!"
    set "MINUTE=!MINUTE: =0!"
    set "PRE_RESTORE_BACKUP=%BACKUP_DIR%\db_pre_restore_!YEAR!!MONTH!!DAY!_!HOUR!!MINUTE!.sqlite3"
    copy "%LOCAL_DB%" "!PRE_RESTORE_BACKUP!" >nul
    if !ERRORLEVEL! EQU 0 (
        echo ✅ Current database backed up to: !PRE_RESTORE_BACKUP!
    )
)

REM Restore database
echo.
echo Restoring database from backup...
copy "%SELECTED_BACKUP%" "%LOCAL_DB%" >nul
if !ERRORLEVEL! EQU 0 (
    echo ✅ Database restored successfully!
    echo    Restored from: %SELECTED_BACKUP%
    echo    To: %LOCAL_DB%
) else (
    echo ❌ Database restore failed
    pause
    exit /b 1
)

REM Verify restore
if exist "%LOCAL_DB%" (
    for %%A in ("%LOCAL_DB%") do set "FILE_SIZE=%%~zA"
    set /a FILE_SIZE_KB=!FILE_SIZE!/1024
    set /a FILE_SIZE_MB=!FILE_SIZE!/1024/1024
    if !FILE_SIZE_MB! GTR 0 (
        echo    File size: !FILE_SIZE_MB! MB
    ) else (
        echo    File size: !FILE_SIZE_KB! KB
    )
) else (
    echo ❌ Error: Database file not found after restore
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Restore completed!
echo ==========================================
echo.
pause

