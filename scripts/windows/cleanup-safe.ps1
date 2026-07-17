param (
    [switch]$CleanRepoCache,
    [switch]$CleanDockerCache,
    [switch]$ArchiveReports,
    [switch]$FullSafeCleanup
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $repoRoot

if ($FullSafeCleanup) {
    $CleanRepoCache = $true
    $CleanDockerCache = $true
    $ArchiveReports = $true
}

Write-Host "CyberSec Assistant safe cleanup"
Write-Host "Project root: $repoRoot"

if (-not ($CleanRepoCache -or $CleanDockerCache -or $ArchiveReports)) {
    Write-Host "Analyze only. Add -CleanRepoCache, -CleanDockerCache, -ArchiveReports, or -FullSafeCleanup to clean."
}

if ($CleanRepoCache) {
    Write-Host "Cleaning generated repo caches..."
    Get-ChildItem -LiteralPath $repoRoot -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.PSIsContainer -and $_.Name -in @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
        } |
        ForEach-Object {
            if ($_.FullName.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force
            }
        }
    Get-ChildItem -LiteralPath $repoRoot -Recurse -Force -File -Include "*.pyc" -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($_.FullName.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $_.FullName -Force
            }
        }
}

if ($ArchiveReports) {
    Write-Host "Archiving stale root reports..."
    $reports = Join-Path $repoRoot "testing\reports"
    $archive = Join-Path $reports ("archive\" + (Get-Date -Format "yyyy-MM-dd"))
    New-Item -ItemType Directory -Force -Path $archive | Out-Null
    $keep = @("FINAL_VALIDATION_REPORT.md", "FINAL_AUDIT_WORKLOG.md", "DELETED_FILES_MANIFEST.md")
    Get-ChildItem -LiteralPath $reports -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notin $keep } |
        ForEach-Object { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $archive $_.Name) -Force }
}

if ($CleanDockerCache) {
    Write-Host "Cleaning safe Docker cache only..."
    docker image prune -f
    docker builder prune -f
}

Write-Host "Done."
