@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

echo ========================================
echo CyberSec Assistant - Docker Rasa Training
echo ========================================

where docker >nul 2>&1 || (
    echo [ERROR] Docker CLI was not found in PATH.
    exit /b 1
)
docker info >nul 2>&1 || (
    echo [ERROR] Docker Desktop is not running.
    exit /b 1
)
if not exist "%PROJECT_ROOT%\rasa\config.yml" (
    echo [ERROR] Rasa config not found.
    exit /b 1
)
if not exist "%PROJECT_ROOT%\rasa\domain.yml" (
    echo [ERROR] Rasa domain not found.
    exit /b 1
)

echo Training inside the Rasa 3.6.20 container...
docker compose run --rm --no-deps --entrypoint rasa rasa train --config /app/config.yml --domain /app/domain.yml --data /app/data --out /app/models
if errorlevel 1 (
    echo [ERROR] Rasa training failed.
    exit /b 1
)

if not exist "%PROJECT_ROOT%\rasa\models\*.tar.gz" (
    echo [ERROR] Training completed without producing a model archive.
    exit /b 1
)

echo [OK] Model generated in rasa\models.
python "%PROJECT_ROOT%\scripts\generate_model_manifest.py"
if errorlevel 1 (
    echo [ERROR] Failed to generate model manifest.
    exit /b 1
)
echo Restarting Rasa-dependent services...
docker compose up -d rasa backend crawler
if errorlevel 1 (
    echo [ERROR] Failed to restart Rasa services.
    exit /b 1
)
exit /b 0
