@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ========================================
echo CyberSec Assistant - Quick Start
echo ========================================
echo.

set "BACKEND_DIR=backend"
set "RASA_DIR=rasa"

echo [1/4] Checking Python environment...
set "PYTHON_CMD="

for %%v in (3.11 3.10 3.9 3.8) do (
    if not defined PYTHON_CMD (
        py -%%v --version >nul 2>&1
        if !errorlevel! == 0 (
            set "PYTHON_CMD=py -%%v"
            echo Found compatible Python %%v via Python Launcher
        )
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if !errorlevel! == 0 (
        set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python not found! Please install Python 3.10 or 3.11
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set PYMAJOR=%%a&set PYMINOR=%%b

if %PYMAJOR% NEQ 3 (
    echo [ERROR] Python 3.x required. Found: %PYVER%
    pause
    exit /b 1
)

echo [OK] Python %PYVER% detected
echo.

if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo Creating Backend virtual environment...
    cd "%BACKEND_DIR%"
    %PYTHON_CMD% -m venv venv
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\pip.exe install -r requirements.txt
    cd ..
)

if exist "%RASA_DIR%\config.yml" (
    if not exist "%RASA_DIR%\venv\Scripts\python.exe" (
        echo Creating Rasa virtual environment...
        cd "%RASA_DIR%"
        %PYTHON_CMD% -m venv venv
        venv\Scripts\python.exe -m pip install --upgrade "pip>=23.1"
        echo Installing Rasa 3.6.20 ^(this may take several minutes^)...
        venv\Scripts\pip.exe install rasa==3.6.20
        venv\Scripts\pip.exe install "setuptools<71.0" "wheel<0.43" "packaging>=20.0,<21.0"
        cd ..
    )
)

echo [2/4] Cleaning up ports...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5055" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5005" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo [3/4] Starting services...

echo Starting Crawler Service on port 8001...
start "Crawler Service" cmd /c "cd backend && set PYTHONPATH=..;. && set PYTHONWARNINGS=ignore && set SQLALCHEMY_SILENCE_UBER_WARNING=1 && venv\Scripts\python.exe -m uvicorn services.crawler_service:crawler_app --host 0.0.0.0 --port 8001"
timeout /t 2 >nul

echo Starting Rasa Actions Server on port 5055...
start "Rasa Actions" cmd /c "cd backend && set PYTHONPATH=..;. && set PYTHONWARNINGS=ignore && set SQLALCHEMY_SILENCE_UBER_WARNING=1 && venv\Scripts\python.exe -m rasa_sdk.__main__ --actions backend.rasa_actions.actions -p 5055"
timeout /t 2 >nul

if exist "rasa\venv\Scripts\python.exe" (
    echo Starting Rasa Assistant on port 5005...
    start "Rasa Assistant" cmd /c "cd rasa && set PYTHONWARNINGS=ignore && set SQLALCHEMY_SILENCE_UBER_WARNING=1 && venv\Scripts\python.exe -m rasa run --enable-api --cors=* --port 5005"
    timeout /t 3 >nul
)

echo Starting Backend Server on port 8000...
start "Backend Server" cmd /c "cd backend && set PYTHONWARNINGS=ignore && set SQLALCHEMY_SILENCE_UBER_WARNING=1 && venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul

echo [4/4] Opening browser...
start http://localhost:8000

echo.
echo ========================================
echo System Started!
echo ========================================
echo Frontend:  http://localhost:8000
echo Backend:   http://localhost:8000/api
echo Crawler:   http://localhost:8001
echo Rasa:      http://localhost:5005
echo.
pause
