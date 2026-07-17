param([switch]$SkipDockerBuild, [switch]$SkipDockerUp)
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
$commands = @()
if (-not $SkipDockerBuild) { $commands += 'docker compose build --no-cache' }
if (-not $SkipDockerUp) { $commands += 'docker compose up -d' }
$commands += @(
  'python testing/scripts/discover_catalog.py',
  'python testing/scripts/generate_required_reports.py',
  'python testing/scripts/docker_check.py',
  'python testing/scripts/http_smoke.py',
  '& .\backend\venv\Scripts\pytest.exe backend/tests -q',
  'Push-Location frontend; npm test; Pop-Location'
)
foreach ($command in $commands) { Write-Host "`n=== $command ===" -ForegroundColor Cyan; Invoke-Expression $command }
