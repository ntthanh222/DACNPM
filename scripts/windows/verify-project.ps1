# verify-project.ps1 - Verify CyberSec Assistant local development stack.

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $projectRoot
$env:COMPOSE_BAKE = "false"

Write-Host "=== CyberSec Assistant Verification ===" -ForegroundColor Cyan
Write-Host "Project root: $projectRoot"

Write-Host "`n=== 1. Checking Docker daemon ===" -ForegroundColor Cyan
docker version | Out-Null
Write-Host "Docker daemon is running." -ForegroundColor Green

Write-Host "`n=== 2. Starting stack via Windows launcher ===" -ForegroundColor Cyan
& (Join-Path $projectRoot "scripts\windows\start.bat")
if ($LASTEXITCODE -ne 0) {
    throw "start.bat failed with exit code $LASTEXITCODE"
}

Write-Host "`n=== 3. Checking HTTP health ===" -ForegroundColor Cyan
$healthUrls = @(
    "http://localhost:8000/health",
    "http://localhost:8002/health",
    "http://localhost:15055/health",
    "http://localhost:15005/",
    "http://localhost:3000/health",
    "http://localhost:9090/-/ready"
)

foreach ($url in $healthUrls) {
    $ok = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                $ok = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    if (-not $ok) {
        throw "Health check failed: $url"
    }
    Write-Host "[OK] $url" -ForegroundColor Green
}

Write-Host "`n=== 4. Running backend tests in Docker ===" -ForegroundColor Cyan
docker exec codex_docker_cybersec_ascii-backend-1 pytest backend/tests -q
if ($LASTEXITCODE -ne 0) {
    throw "Backend tests failed with exit code $LASTEXITCODE"
}

Write-Host "`n=== 5. Running frontend unit/regression tests ===" -ForegroundColor Cyan
Push-Location frontend
try {
    npm test
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend tests failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host "`n=== Verification Complete: SUCCESS ===" -ForegroundColor Green
