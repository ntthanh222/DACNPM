@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"
rem Docker Compose Bake opens a BuildKit session with a generated shared key.
rem On some Docker Desktop/Compose versions that session header breaks when the
rem project path contains non-ASCII characters, so keep classic Compose build
rem behavior for this Windows launcher.
set "COMPOSE_BAKE=false"
set "COMPOSE_PROJECT_DIR=%PROJECT_ROOT%"
set "ASCII_PROJECT_ROOT=D:\codex_docker_cybersec_ascii"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = [IO.Path]::GetFullPath($env:COMPOSE_PROJECT_DIR); if ($p.ToCharArray() | Where-Object { [int]$_ -gt 127 }) { exit 10 } else { exit 0 }"
if "%ERRORLEVEL%"=="10" (
    echo [INFO] Project path contains non-ASCII characters.
    echo [INFO] Syncing source to ASCII Docker workspace: %ASCII_PROJECT_ROOT%
    if /I "%CD%"=="%ASCII_PROJECT_ROOT%" (
        echo [ERROR] Refusing to sync: source and destination are the same.
        exit /b 1
    )
    if not exist "%ASCII_PROJECT_ROOT%" mkdir "%ASCII_PROJECT_ROOT%"
    robocopy "%PROJECT_ROOT%" "%ASCII_PROJECT_ROOT%" /E /XD ".git" ".venv" "venv" "node_modules" "frontend\node_modules" "backend\venv" "backend\.venv" "backend\test_env" "backend\test_venv" "backend\test_rasa_venv" ".pytest_cache" "__pycache__" "cache" /XF "*.pyc" >nul
    if errorlevel 8 (
        echo [ERROR] Failed to sync project to ASCII Docker workspace.
        exit /b 1
    )
    cd /d "%ASCII_PROJECT_ROOT%"
)

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
echo Actions: http://localhost:15055
echo Rasa:    http://localhost:15005
echo Frontend: http://localhost:3000
start "" http://localhost:3000
exit /b 0
