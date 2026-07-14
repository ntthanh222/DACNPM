@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

echo ====================================
echo Security News Crawler - Docker
echo ====================================
docker info >nul 2>&1 || (
    echo [ERROR] Docker Desktop is not running.
    exit /b 1
)

docker compose run --rm --no-deps crawler python -m backend.scripts.crawl_security_news --headless --articles 15
if errorlevel 1 (
    echo [ERROR] Crawler failed.
    exit /b 1
)
echo [OK] Crawler completed successfully.
exit /b 0
