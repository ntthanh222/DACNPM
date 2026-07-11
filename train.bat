@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ========================================
echo CyberSec Assistant - Quick Train
echo ========================================
echo.

set "RASA_DIR=rasa"

REM Auto-detect Python
echo [1/3] Checking Python...
set "PYTHON_CMD="

REM Try to detect Python Launcher (py) with compatible versions (3.11 3.10 3.9 3.8)
for %%v in (3.11 3.10 3.9 3.8) do (
    if not defined PYTHON_CMD (
        py -%%v --version >nul 2>&1
        if !errorlevel! == 0 (
            set "PYTHON_CMD=py -%%v"
            echo Found compatible Python %%v via Python Launcher
        )
    )
)

REM If py launcher didn't find a compatible version, check default python command
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

REM Check Python version (3.8-3.11 required for Rasa 3.6.20)
echo Checking Python version compatibility...
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set PYMAJOR=%%a&set PYMINOR=%%b

REM Rasa 3.6.20 requires Python 3.8-3.11
if %PYMAJOR% NEQ 3 (
    echo [ERROR] Python 3.x required. Found: %PYVER%
    echo [ERROR] Please install Python 3.10 or 3.11
    pause
    exit /b 1
)

if %PYMINOR% LSS 8 (
    echo [ERROR] Python 3.8+ required. Found: %PYVER%
    echo [ERROR] Please install Python 3.10 or 3.11
    pause
    exit /b 1
)

if %PYMINOR% GTR 11 (
    echo [ERROR] Python 3.11 or earlier required. Found: %PYVER%
    echo [ERROR] Rasa 3.6.20 is not compatible with Python 3.12+
    echo.
    echo Solution:
    echo   1. Download Python 3.11: https://www.python.org/downloads/
    echo   2. Install it alongside your current Python
    echo   3. Re-run this script - it will auto-detect Python 3.11
    pause
    exit /b 1
)

echo [OK] Python %PYVER% is compatible with Rasa 3.6.20
echo.

REM Setup Rasa venv if needed
if not exist "%RASA_DIR%\venv\Scripts\python.exe" (
    echo Creating Rasa virtual environment...
    cd "%RASA_DIR%"
    %PYTHON_CMD% -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment
        cd ..
        pause
        exit /b 1
    )
    echo Upgrading pip...
    venv\Scripts\python.exe -m pip install --upgrade "pip>=23.1"
    echo Installing Rasa 3.6.20 (this may take several minutes^)...
    venv\Scripts\pip.exe install rasa==3.6.20
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Rasa. Removing broken venv...
        rmdir /s /q venv
        cd ..
        pause
        exit /b 1
    )
    cd ..
)

REM Verify Rasa is actually installed (use pip show, not import, to avoid local rasa/ shadowing)
echo Verifying Rasa installation...
"%RASA_DIR%\venv\Scripts\pip.exe" show rasa >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Rasa not found in venv. Installing...
    echo This may take several minutes...
    cd "%RASA_DIR%"
    venv\Scripts\python.exe -m pip install --upgrade "pip>=23.1"
    venv\Scripts\pip.exe install rasa==3.6.20
    if errorlevel 1 (
        echo [ERROR] Failed to install Rasa.
        cd ..
        pause
        exit /b 1
    )
    cd ..
)

REM Ensure compatible dependency versions for Rasa 3.6.20:
echo Checking dependencies...
"%RASA_DIR%\venv\Scripts\pip.exe" install "setuptools<71.0" "wheel<0.43" "packaging>=20.0,<21.0" >nul 2>&1

REM Check if Rasa config exists
if not exist "%RASA_DIR%\config.yml" (
    echo [ERROR] Rasa config not found in %RASA_DIR%
    pause
    exit /b 1
)

REM Train Rasa
echo [2/3] Training Rasa model...
echo.
cd "%RASA_DIR%"
set PYTHONWARNINGS=ignore
set SQLALCHEMY_SILENCE_UBER_WARNING=1
venv\Scripts\python.exe -m rasa train

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Training failed!
    cd ..
    pause
    exit /b 1
)
cd ..

REM Clean up old models
echo [3/4] Cleaning up old models...
"%RASA_DIR%\venv\Scripts\python.exe" "%~dp0backend\scripts\cleanup_models.py" --keep 3

REM Show result
echo [4/4] Training completed!
echo.
echo Trained models:
dir /b "%RASA_DIR%\models\*.tar.gz" 2>nul
echo.

echo Next:
echo   - Run start.bat to test the model
echo   - Or test manually: cd rasa ^&^& venv\Scripts\python.exe -m rasa shell
echo.
pause
