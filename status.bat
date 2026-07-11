@echo off
chcp 65001 >nul 2>&1
REM ========================================
REM CyberSec Assistant - Service Status Checker
REM Shows the status of all CyberSec services
REM ========================================

setlocal enabledelayedexpansion
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ========================================
echo CyberSec Assistant - Service Status
echo ========================================
echo.

REM Configuration
set PORTS=8000 5055 5005
set PORT_NAMES=Backend:8000 Actions:5055 Rasa:5005
set "BACKEND_PYTHON=backend\venv\Scripts\python.exe"
set "RASA_PYTHON=rasa\venv\Scripts\python.exe"

echo Checking services...
echo.

set TOTAL=0
set RUNNING=0

for %%p in (%PORTS%) do (
    set /a TOTAL+=1
    set PORT_STATUS=0

    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%%p " ^| find "LISTENING"') do (
        set PORT_STATUS=1
        set /a RUNNING+=1

        REM Get process name
        for /f "tokens=1" %%n in ('tasklist /FI "PID eq %%a" /NH 2^>nul ^| find /v "INFO:"') do (
            set PROC_NAME=%%n
        )

        REM Get process uptime
        for /f "tokens=2" %%u in ('tasklist /FI "PID eq %%a" /NH /FO CSV 2^>nul') do (
            set UPTIME=%%u
        )

        echo [✓] Port %%p: RUNNING
        echo     Process: !PROC_NAME!
        echo     PID: %%a
        echo.
    )

    if !PORT_STATUS!==0 (
        echo [✗] Port %%p: STOPPED
        echo.
    )
)

echo ========================================
echo Summary
echo ========================================
echo.
echo Services Running: %RUNNING%/%TOTAL%
echo.

if %RUNNING%==%TOTAL% (
    echo [✓] All services are running!
    echo.
    echo You can access:
    echo   • Frontend: http://localhost:8000
    echo   • API:      http://localhost:8000/api
    echo   • Health:   http://localhost:8000/health
    if exist "rasa\config.yml" (
        echo   • Rasa:    http://localhost:5005
        echo   • Actions: http://localhost:5055
    )
    echo.
) else if %RUNNING%==0 (
    echo [✗] No services are running
    echo.
    echo To start all services, run:
    echo   start.bat
    echo.
) else (
    echo [!] Some services are not running
    echo.
    echo To restart all services, run:
    echo   stop.bat
    echo   start.bat
    echo.
)

REM ========================================
echo Health Checks
echo ========================================
echo.

REM Check Backend Health
echo Checking Backend API...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 2; Write-Host '  [✓] Backend API is healthy' } catch { Write-Host '  [✗] Backend API is not responding' }" 2>nul
echo.

REM Check Rasa Health
echo Checking Rasa API...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5005' -TimeoutSec 2; Write-Host '  [✓] Rasa API is responding' } catch { Write-Host '  [!] Rasa API is not responding or not running' }" 2>nul
echo.

REM Check Actions Server
echo Checking Actions Server...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5055/webhook' -TimeoutSec 2 -Method Post -Body '{}'; Write-Host '  [✓] Actions Server is responding' } catch { Write-Host '  [!] Actions Server is not responding or not running' }" 2>nul
echo.

echo ========================================
echo System Information
echo ========================================
echo.
echo Python Version:
python --version 2>nul
echo.
echo Working Directory: %CD%
echo Project Directory: %~dp0
echo.

REM Check Rasa Installation
echo Rasa Installation:
"%RASA_PYTHON%" -c "import rasa; print('  Installed: Rasa', rasa.__version__)" 2>nul
if errorlevel 1 (
    echo  [!] Rasa is not installed
    echo  Install with: cd rasa ^&^& venv\Scripts\activate ^&^& pip install rasa==3.6.20
)
echo.

REM Check Trained Models
echo Trained Models:
if exist "rasa\models\*.tar.gz" (
    for /f "delims=" %%a in ('dir /b "rasa\models\*.tar.gz" 2^>nul') do (
        echo   • %%a
    )
) else (
    echo  [!] No trained models found
    echo  Train a model with: train.bat
)
echo.

echo ========================================
echo Available Commands
echo ========================================
echo.
echo   start.bat   - Start all services
echo   stop.bat    - Stop all services
echo   train.bat   - Train Rasa model
echo   status.bat  - Show this status screen
echo   clean.bat   - Clean temporary files
echo.
echo ========================================
pause
