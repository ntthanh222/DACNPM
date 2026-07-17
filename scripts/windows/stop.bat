@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"
set "COMPOSE_BAKE=false"
set "COMPOSE_PROJECT_DIR=%PROJECT_ROOT%"
set "ASCII_PROJECT_ROOT=D:\codex_docker_cybersec_ascii"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = [IO.Path]::GetFullPath($env:COMPOSE_PROJECT_DIR); if ($p.ToCharArray() | Where-Object { [int]$_ -gt 127 }) { exit 10 } else { exit 0 }"
if "%ERRORLEVEL%"=="10" (
    if exist "%ASCII_PROJECT_ROOT%\docker-compose.yml" cd /d "%ASCII_PROJECT_ROOT%"
)

echo Stopping CyberSec Docker services...
docker compose stop
if errorlevel 1 (
    echo [ERROR] Docker Compose stop failed.
    exit /b 1
)
echo [OK] Docker services stopped. Volumes were preserved.
exit /b 0
