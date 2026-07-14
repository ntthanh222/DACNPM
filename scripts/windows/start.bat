@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

echo ========================================
echo CyberSec Assistant - Docker Start
echo ========================================

where docker >nul 2>&1 || (
    echo [ERROR] Docker CLI was not found in PATH.
    exit /b 1
)
docker info >nul 2>&1 || (
    echo [ERROR] Docker Desktop is not running.
    exit /b 1
)

if not exist "%PROJECT_ROOT%\rasa\models\*.tar.gz" (
    echo [ERROR] No Rasa model found in rasa\models.
    echo Run scripts\windows\train.bat first.
    exit /b 1
)

echo Starting Docker services...
rem The crawler service is defined in docker-compose.yml with --port 8002.
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start the services.
    exit /b 1
)

echo.
echo [OK] Services started.
echo Backend: http://localhost:8000
echo Crawler: http://localhost:8002
echo Actions: http://localhost:5055
echo Rasa:    http://localhost:5005
echo Frontend: http://localhost:3000
start "" http://localhost:3000
exit /b 0
