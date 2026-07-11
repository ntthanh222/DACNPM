@echo off
REM Security News Crawler - Windows Batch Script
REM Chạy crawler tin tức bảo mật

echo ====================================
echo Security News Crawler
echo ====================================
echo.

REM Thiết lập biến
set SCRIPT_DIR=%~dp0
cd %SCRIPT_DIR%..

REM Chạy crawler
python scripts\crawl_security_news.py --headless --articles 15

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Crawler completed successfully!
) else (
    echo.
    echo ❌ Crawler failed with error code: %ERRORLEVEL%
)

echo.
pause
