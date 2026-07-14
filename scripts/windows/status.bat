@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0..\.."
set PORTS=8000 8002 5055 5005
cd /d "%PROJECT_ROOT%"

echo ========================================
echo CyberSec Assistant - Docker Status
echo ========================================

where docker >nul 2>&1 || (
    echo [ERROR] Docker CLI was not found in PATH.
    exit /b 1
)
docker compose ps

echo.
echo Port status:
for %%p in (%PORTS%) do (
    set "FOUND=0"
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":%%p .*LISTENING"') do (
        set "FOUND=1"
        echo [RUNNING] Port %%p - PID %%a
    )
    if !FOUND!==0 echo [STOPPED] Port %%p
)

echo.
echo HTTP health:
for %%u in ("http://localhost:8000/health" "http://localhost:8002/health" "http://localhost:5055/health" "http://localhost:5005/" "http://localhost:3000/health" "http://localhost:9090/-/ready") do (
    curl.exe -fsS -o nul "%%~u" >nul 2>&1
    if errorlevel 1 (echo [FAIL] %%~u) else (echo [OK]   %%~u)
)
exit /b 0
