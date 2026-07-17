$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $root
try {
  python testing/scripts/discover_catalog.py
  python testing/scripts/docker_check.py
  python testing/scripts/http_smoke.py
  Push-Location backend
  & .\venv\Scripts\pytest.exe tests -q
  Pop-Location
  Push-Location frontend
  npm test
  npm run e2e
  Pop-Location
} finally { Pop-Location }
