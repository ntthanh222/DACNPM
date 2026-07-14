@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

echo Stopping CyberSec Docker services...
docker compose stop
if errorlevel 1 (
    echo [ERROR] Docker Compose stop failed.
    exit /b 1
)
echo [OK] Docker services stopped. Volumes were preserved.
exit /b 0
