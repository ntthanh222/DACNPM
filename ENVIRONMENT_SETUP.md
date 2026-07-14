# Environment setup

## Docker Compose (recommended)

Rasa and its custom action server run entirely in Docker. The Windows batch
files use Docker Compose and do not require `rasa/venv` or a manually started
action server.

Install and start Docker Desktop, then train the Rasa model once:

```powershell
.\scripts\windows\train.bat
.\scripts\windows\start.bat
.\scripts\windows\status.bat
```

Training writes the generated `.tar.gz` model to `rasa/models/`. That directory
is ignored by Git but is bind-mounted into the Rasa container. If the model is
missing, Rasa intentionally remains unhealthy until `train.bat` succeeds.

Useful Docker commands:

```powershell
docker compose config --quiet
docker compose logs -f rasa rasa-actions
docker compose stop
```

## Optional local Python environments

The project still documents two virtual environments for local diagnostics:

- `backend/venv`: Python 3.14 for FastAPI, crawler and backend services.
- `rasa/venv`: Python 3.10 for fallback local Rasa diagnostics only.

Create or restore them from PowerShell:

```powershell
py -3.14 -m venv backend/venv
backend/venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt

py -3.10 -m venv rasa/venv
rasa/venv/Scripts/python.exe -m pip install -r rasa/requirements-lock.txt
```

The Docker-based commands are located in `scripts/windows/`:

```text
start.bat
status.bat
stop.bat
run_crawler_windows.bat
train.bat
```

Virtual environments, caches, generated Rasa models, Chroma data, logs,
compiled extensions and local environment files are intentionally excluded
from Git. Keep secrets in a local `.env.local` and rotate any credentials that
have been exposed outside the machine.
