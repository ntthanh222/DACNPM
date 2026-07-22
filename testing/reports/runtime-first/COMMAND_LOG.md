# Command Log

This log chronicles all key terminal and container commands run during diagnostics, refactoring, and validation.

## 1. Diagnostics & Checkpointing
```powershell
# Verify current branch and untracked changes
git status --short
git branch --show-current

# Switched to new stabilization branch
git checkout -b checkpoint-stabilization

# Review active containers
docker compose ps
```

## 2. Model Manifest Generation
```powershell
# Generate model manifest pointer file current-model.json
python "d:\Đồ án CNPM\scripts\generate_model_manifest.py"
```

## 3. Restarting Stack & Sync
```powershell
# Restart containers to verify startup entries
docker compose restart rasa backend crawler
docker compose restart frontend
```

## 4. Test Verification
```powershell
# Run backend pytest suite
docker compose exec backend pytest backend/tests

# Run Rasa data validation
docker compose run --rm --no-deps --entrypoint rasa rasa data validate --domain /app/domain.yml --data /app/data

# Run Rasa NLU cross-validation
docker compose run --rm --no-deps --entrypoint rasa rasa test nlu --nlu /app/data/nlu.yml --config /app/config.yml --cross-validation --folds 5
```

## 5. End-to-End Browser Verification
```powershell
# Set admin password and trigger browser automation
$env:E2E_ADMIN_PASSWORD="DevAdmin-[REDACTED]"
node frontend/tests/browser_automation.js
```
