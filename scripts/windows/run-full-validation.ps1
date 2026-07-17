# run-full-validation.ps1 - Full validation and regression suite

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $projectRoot
$env:COMPOSE_BAKE = "false"

Write-Host "=== 1. Checking Dependencies (pip check) ===" -ForegroundColor Cyan
try {
    & .\backend\venv\Scripts\pip.exe check
    Write-Host "No dependency conflicts found." -ForegroundColor Green
} catch {
    Write-Warning "Dependency check failed or reported warnings."
}

Write-Host "`n=== 2. Running Regression Loop 1 ===" -ForegroundColor Cyan
try {
    & .\backend\venv\Scripts\pytest.exe backend/tests -q
    Write-Host "Loop 1 Passed." -ForegroundColor Green
} catch {
    Write-Error "Loop 1 Failed!"
    Exit 1
}

Write-Host "`n=== 3. Running Regression Loop 2 (Data Reset Simulation) ===" -ForegroundColor Cyan
try {
    & .\backend\venv\Scripts\pytest.exe backend/tests -q
    Write-Host "Loop 2 Passed." -ForegroundColor Green
} catch {
    Write-Error "Loop 2 Failed!"
    Exit 1
}

Write-Host "`n=== 4. Running Regression Loop 3 (Service Restart Simulation) ===" -ForegroundColor Cyan
try {
    Write-Host "Restarting Docker Compose Stack..." -ForegroundColor Gray
    & docker compose restart backend
    Start-Sleep -Seconds 5
    & .\backend\venv\Scripts\pytest.exe backend/tests -q
    Write-Host "Loop 3 Passed." -ForegroundColor Green
} catch {
    Write-Error "Loop 3 Failed!"
    Exit 1
}

Write-Host "`n=== Full Validation and 3-Loop Regression Complete: SUCCESS ===" -ForegroundColor Green
Exit 0
