@echo off
rem Google Sheets Sync Script for CS 15 Tutor Database
rem Double-click this file to sync your data to Google Sheets

echo.
echo ====================================================
echo   CS 15 Tutor - Google Sheets Data Sync
echo ====================================================
echo.

rem Check if we're in the right directory
if not exist "google_sheets_sync.py" (
    echo ❌ Error: google_sheets_sync.py not found
    echo Make sure this file is in the responses-api-server directory
    pause
    exit /b 1
)

rem Check if database exists
if not exist "cs15_tutor_logs.db" (
    echo ❌ Error: Database file not found
    echo Make sure the API server has been run to create data
    pause
    exit /b 1
)

rem Check if configuration exists
if not exist "sheets_config.json" (
    echo ⚙️  No configuration found. Running setup...
    echo.
    python google_sheets_sync.py setup
    if errorlevel 1 (
        echo ❌ Setup failed
        pause
        exit /b 1
    )
    echo.
    echo ✅ Setup completed!
    echo.
)

rem Perform full sync
echo 🔄 Syncing data to Google Sheets...
echo.
python google_sheets_sync.py sync

if errorlevel 1 (
    echo.
    echo ❌ Sync failed! Check the error messages above.
    echo.
    echo Troubleshooting tips:
    echo - Make sure you're connected to the internet
    echo - Check that your Google credentials are valid
    echo - Verify the spreadsheet still exists
    echo.
) else (
    echo.
    echo ✅ Sync completed successfully!
    echo Your Google Sheets dashboard has been updated.
    echo.
)

echo Press any key to exit...
pause >nul 