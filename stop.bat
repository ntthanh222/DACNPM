@echo off
chcp 65001 >nul 2>&1
REM ========================================
REM CyberSec Assistant - Stop All Services
REM Safely stops all running CyberSec services
REM ========================================

setlocal enabledelayedexpansion

echo ========================================
echo CyberSec Assistant - Stopping Services
echo ========================================
echo.

REM Ports used by CyberSec services
set PORTS=8000 5055 5005

echo Checking for running services on ports: %PORTS%
echo.

for %%p in (%PORTS%) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%%p " ^| find "LISTENING"') do (
        echo [FOUND] Process %%a is using port %%p

        REM Get process name
        for /f "tokens=1" %%n in ('tasklist /FI "PID eq %%a" /NH ^| find /v "INFO:"') do (
            set "PROC_NAME=%%n"
        )

        REM Try to terminate gracefully first
        echo Attempting to stop !PROC_NAME! (PID %%a)...
        taskkill /PID %%a /T >nul 2>&1

        if !errorlevel!==0 (
            echo [SUCCESS] Stopped !PROC_NAME! on port %%p
        ) else (
            echo [FAILED] Could not stop !PROC_NAME! on port %%p
            echo You may need to close it manually or run as Administrator
        )
        echo.
    )
)

echo ========================================
echo Service Cleanup Summary
echo ========================================
echo.

REM Check if any processes are still running
set STILL_RUNNING=0
for %%p in (%PORTS%) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%%p " ^| find "LISTENING"') do (
        set STILL_RUNNING=1
        echo [WARNING] Port %%p is still in use by process %%a
    )
)

if %STILL_RUNNING%==0 (
    echo All CyberSec services have been stopped successfully.
    echo.
    echo You can now start fresh with: start.bat
) else (
    echo.
    echo Some services could not be stopped automatically.
    echo.
    echo To stop them manually:
    echo 1. Open Task Manager (Ctrl+Shift+Esc)
    echo 2. Find the processes listed above
    echo 3. End task
    echo.
    echo Or run this script as Administrator for elevated privileges.
)

echo.
echo ========================================
echo Cleaning up Python cache files...
echo ========================================
echo.

REM Clean up __pycache__ directories
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        echo Removing: %%d
        rd /s /q "%%d" 2>nul
    )
)

REM Clean up .pyc files
del /s /q *.pyc 2>nul

REM Clean up .pyo files
del /s /q *.pyo 2>nul

echo.
echo [SUCCESS] Python cache files cleaned up.
echo.

echo.
echo ========================================
pause
