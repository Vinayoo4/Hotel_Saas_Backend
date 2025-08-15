@echo off
echo Hotel Management Backend Backup Script
echo ======================================

:: Configuration
set BACKUP_DIR=.\backups
set DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set DATE=%DATE: =0%
set DB_NAME=hotel_management
set DB_USER=hotel_user
set DB_HOST=localhost
set DB_PORT=5432

:: Create backup directory if it doesn't exist
if not exist "%BACKUP_DIR%" (
    echo Creating backup directory: %BACKUP_DIR%
    mkdir "%BACKUP_DIR%"
)

echo Starting backup process at %DATE%...

:: Check if PostgreSQL is accessible
echo Checking PostgreSQL connection...
pg_isready -h %DB_HOST% -p %DB_PORT% -U %DB_USER% >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cannot connect to PostgreSQL. Check your database settings.
    pause
    exit /b 1
)

:: Create database backup
echo Creating database backup...
set DB_BACKUP_FILE=%BACKUP_DIR%\db_backup_%DATE%.sql

pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% > "%DB_BACKUP_FILE%" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Database backup created: %DB_BACKUP_FILE%
    
    :: Compress the backup using PowerShell
    echo Compressing database backup...
    powershell -Command "Compress-Archive -Path '%DB_BACKUP_FILE%' -DestinationPath '%DB_BACKUP_FILE%.zip' -Force"
    if %ERRORLEVEL% EQU 0 (
        echo Database backup compressed: %DB_BACKUP_FILE%.zip
        del "%DB_BACKUP_FILE%"
    ) else (
        echo WARNING: Could not compress database backup
    )
) else (
    echo ERROR: Database backup failed
    pause
    exit /b 1
)

:: Create file backup
echo Creating file backup...
set FILES_BACKUP_FILE=%BACKUP_DIR%\files_backup_%DATE%.zip

:: Use PowerShell to create zip archive
powershell -Command "Compress-Archive -Path 'uploads\*', 'ml_models\*', 'data\*' -DestinationPath '%FILES_BACKUP_FILE%' -Force"
if %ERRORLEVEL% EQU 0 (
    echo File backup created: %FILES_BACKUP_FILE%
) else (
    echo ERROR: File backup failed
    pause
    exit /b 1
)

:: Cleanup old backups (keep for 30 days)
echo Cleaning up old backups...
forfiles /p "%BACKUP_DIR%" /s /m *.zip /d -30 /c "cmd /c del @path" >nul 2>&1
echo Old backups cleaned up

:: Show backup summary
echo.
echo Backup process completed successfully!
echo.
echo Available backups:
dir /b "%BACKUP_DIR%\*.zip" 2>nul

:: Show disk space
echo.
echo Disk space information:
powershell -Command "Get-WmiObject -Class Win32_LogicalDisk -Filter 'DeviceID=\'C:\'' | Select-Object DeviceID, @{Name='Size(GB)';Expression={[math]::Round($_.Size/1GB,2)}}, @{Name='FreeSpace(GB)';Expression={[math]::Round($_.FreeSpace/1GB,2)}} | Format-Table -AutoSize"

echo.
echo Backup completed at %time%
pause
