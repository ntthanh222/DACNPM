from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_backend(relative_path: str) -> str:
    return (PROJECT_ROOT / "backend" / relative_path).read_text(encoding="utf-8")


def read_project(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_proxy_image_does_not_use_unsupported_httpx_limit():
    source = read_backend("api/proxy.py")

    assert "max_read" not in source


def test_backend_exposes_prometheus_metrics_endpoint():
    source = read_backend("api/system.py")

    assert '@router.get("/metrics"' in source


def test_crawler_default_port_does_not_conflict_with_chromadb():
    crawler_source = read_backend("services/crawler_service.py")
    start_script = read_project("scripts/windows/start.bat")
    status_script = read_project("scripts/windows/status.bat")

    assert 'CRAWLER_PORT = int(os.getenv("CRAWLER_PORT", "8002"))' in crawler_source
    assert "--port 8002" in start_script
    assert "set PORTS=8000 8002 15055 15005" in status_script


def test_prometheus_only_scrapes_available_compose_services():
    prometheus = read_project("prometheus.yml")

    assert "backend:8000" in prometheus
    assert "postgres:5432" not in prometheus
    assert "node-exporter:9100" not in prometheus
    assert "cadvisor:8080" not in prometheus
    assert "redis:6379" not in prometheus


def test_analyst_read_routes_use_privileged_client_without_admin_only_dependency():
    deps = read_backend("api/deps.py")
    monitoring = read_backend("api/v1/admin/system_monitoring.py")
    rag = read_backend("api/v1/admin/rag_operations.py")

    assert "async def get_privileged_client" in deps
    assert "admin_client = Depends(get_privileged_client)" in monitoring
    assert "admin_client = Depends(get_privileged_client)" in rag


def test_global_report_exports_require_elevated_roles():
    reports = read_backend("api/reports.py")

    assert "def export_assets_report" in reports
    assert "def export_incidents_report" in reports
    assert "def export_audit_logs_report" in reports
    assert "current_user_id: UUID = Depends(require_admin_or_analyst)" in reports
    assert "current_user_id: UUID = Depends(require_admin)" in reports


def test_nlu_retraining_is_docker_only():
    source = read_backend("api/v1/admin/nlu_training.py")

    assert '"compose"' in source
    assert '"--entrypoint", "rasa"' in source
    assert "rasa/venv" not in source
    assert 'rasa_python = ' not in source


def test_qa_backend_compose_builds_backend_target_without_browser_packages():
    compose = read_project("docker-compose.test.yml")
    dockerfile = read_backend("Dockerfile")

    assert "target: development" in compose
    assert 'INSTALL_BROWSER: "false"' in compose
    assert "ARG INSTALL_BROWSER=true" in dockerfile
    assert 'if [ "$INSTALL_BROWSER" = "true" ]' in dockerfile


def test_rag_runtime_imports_are_package_absolute():
    for relative_path in (
        "api/hybrid_chatbot.py",
        "services/rag_service.py",
        "api/v1/admin/rag_operations.py",
    ):
        source = read_backend(relative_path)
        assert "from rag." not in source


def test_gemini_key_aliases_are_supported():
    settings_source = read_backend("config/settings.py")

    assert 'AliasChoices("LLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")' in settings_source
    assert "LLM_API_KEY=${GEMINI_API_KEY}" in read_project("docker-compose.yml")
    assert 'llm_model: str = Field(default="gemini-2.5-flash"' in settings_source


@pytest.mark.asyncio
async def test_security_analyst_can_read_but_cannot_use_admin_dependency(monkeypatch):
    from backend.api.deps import get_privileged_client, require_admin, require_admin_or_analyst

    user_id = uuid4()
    analyst = SimpleNamespace(role="security_analyst", is_active=True)
    monkeypatch.setattr("backend.repositories.users.get_user", lambda _: analyst)

    assert await require_admin_or_analyst(user_id) == user_id
    with pytest.raises(Exception) as error:
        await require_admin(user_id)
    assert error.value.status_code == 403

    client = object()
    monkeypatch.setattr("backend.database.connection.get_supabase_admin_client", lambda: client)
    assert await get_privileged_client(user_id) is client
