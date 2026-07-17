import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.matching_service import MatchingService
from backend.services.audit_service import log_audit_event, get_audit_logs
from backend.api.deps import require_current_user_id, require_admin_or_analyst, require_admin

client = TestClient(app)

# Helper token data mock
@pytest.fixture(autouse=True)
def mock_auth_dependencies(monkeypatch):
    # Mock require_current_user_id to return a fixed UUID using FastAPI's overrides
    user_uuid = uuid4()
    app.dependency_overrides[require_current_user_id] = lambda: user_uuid
    app.dependency_overrides[require_admin_or_analyst] = lambda: user_uuid
    app.dependency_overrides[require_admin] = lambda: user_uuid
    
    # Force mock database availability to False to run in-memory fallback during unit testing
    monkeypatch.setattr("backend.database.connection.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.api.assets.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.api.cve_watchlist.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.api.alerts.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.api.incidents.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.api.notifications.DATABASE_AVAILABLE", False)
    monkeypatch.setattr("backend.services.audit_service.DATABASE_AVAILABLE", False)
    
    yield user_uuid
    app.dependency_overrides.clear()



def test_risk_scoring_logic():
    # Test low risk
    risk = MatchingService.calculate_risk_score(cvss_score=3.5, criticality="low")
    assert risk["score"] == 26.0
    assert risk["severity"] == "low"

    # Test critical risk (CVSS 9.8, critical asset, internet exposed, known exploited, no patch)
    risk_crit = MatchingService.calculate_risk_score(
        cvss_score=9.8,
        criticality="critical",
        internet_exposure=True,
        known_exploited=True,
        patch_available=False
    )
    # 58.8 (cvss) + 20 (crit) + 10 (exp) + 10 (exploit) + 5 (no patch) = 103.8 -> capped at 100
    assert risk_crit["score"] == 100.0
    assert risk_crit["severity"] == "critical"

def test_cpe_matching():
    # Exact match
    matched, conf, reason = MatchingService.match_cpe(
        "cpe:2.3:a:nginx:nginx:1.20.1:*:*:*:*:*:*:*",
        "cpe:2.3:a:nginx:nginx:1.20.1:*:*:*:*:*:*:*"
    )
    assert matched is True
    assert conf == 1.0

    # Wildcard in CVE
    matched_wc, conf_wc, _ = MatchingService.match_cpe(
        "cpe:2.3:a:apache:http_server:2.4.48:*:*:*:*:*:*:*",
        "cpe:2.3:a:apache:http_server:*:*:*:*:*:*:*:*"
    )
    assert matched_wc is True
    assert conf_wc == 1.0

    # Version mismatch
    matched_mis, _, _ = MatchingService.match_cpe(
        "cpe:2.3:a:nginx:nginx:1.20.1:*:*:*:*:*:*:*",
        "cpe:2.3:a:nginx:nginx:1.21.0:*:*:*:*:*:*:*"
    )
    assert matched_mis is False

def test_assets_endpoints():
    # Create asset
    asset_payload = {
        "name": "Production Database Server",
        "asset_type": "database",
        "hostname": "db-prod-01",
        "ip_address": "10.0.1.5",
        "os": "Ubuntu 22.04 LTS",
        "vendor": "postgresql",
        "product": "postgresql",
        "version": "14.5",
        "cpe": "cpe:2.3:a:postgresql:postgresql:14.5:*:*:*:*:*:*:*",
        "owner": "DBA Team",
        "department": "IT",
        "environment": "production",
        "criticality": "critical",
        "internet_exposure": False,
        "status": "active",
        "notes": "Primary database server holding customer records."
    }
    
    # POST /api/assets
    response = client.post("/api/assets/", json=asset_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Production Database Server"
    asset_id = data["id"]

    # GET /api/assets
    response_list = client.get("/api/assets/")
    assert response_list.status_code == 200
    assert len(response_list.json()) >= 1

    # GET /api/assets/{id}
    response_get = client.get(f"/api/assets/{asset_id}")
    assert response_get.status_code == 200
    assert response_get.json()["hostname"] == "db-prod-01"

    # PUT /api/assets/{id}
    response_put = client.put(f"/api/assets/{asset_id}", json={"notes": "Updated notes"})
    assert response_put.status_code == 200
    assert response_put.json()["notes"] == "Updated notes"

    # GET /api/assets/{id}/matching-cves
    response_match = client.get(f"/api/assets/{asset_id}/matching-cves")
    assert response_match.status_code == 200
    assert "matches" in response_match.json()

    # DELETE /api/assets/{id}
    response_del = client.delete(f"/api/assets/{asset_id}")
    assert response_del.status_code == 200

def test_cve_watchlist_endpoints():
    # Watch a CVE
    watchlist_payload = {
        "cve_id": "CVE-2021-44228",
        "notes": "Apache Log4j RCE vulnerability.",
        "asset_id": None,
        "notification_preference": "all"
    }
    response = client.post("/api/cve-watchlist/", json=watchlist_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["cve_id"] == "CVE-2021-44228"
    watch_id = data["id"]

    # List watchlist
    response_list = client.get("/api/cve-watchlist/")
    assert response_list.status_code == 200
    assert len(response_list.json()) >= 1

    # Unwatch CVE
    response_del = client.delete(f"/api/cve-watchlist/{watch_id}")
    assert response_del.status_code == 200

def test_alerts_endpoints():
    # Create alert
    alert_payload = {
        "title": "Unusual Prompt Injection Detected",
        "description": "High rate of prompt injection indicators flagged by NLU filter.",
        "severity": "high",
        "alert_type": "prompt_injection",
        "status": "unread",
        "related_entity_type": "user",
        "related_entity_id": str(uuid4())
    }
    response = client.post("/api/alerts/", json=alert_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Unusual Prompt Injection Detected"
    alert_id = data["id"]

    # List alerts
    response_list = client.get("/api/alerts/")
    assert response_list.status_code == 200
    assert len(response_list.json()) >= 1

    # Acknowledge alert
    response_ack = client.put(f"/api/alerts/{alert_id}/acknowledge")
    assert response_ack.status_code == 200
    assert response_ack.json()["status"] == "acknowledged"

    # Resolve alert
    response_res = client.put(f"/api/alerts/{alert_id}/resolve")
    assert response_res.status_code == 200
    assert response_res.json()["status"] == "resolved"

def test_incidents_endpoints():
    # Create incident
    incident_payload = {
        "title": "Data Leak Investigation",
        "description": "Potential customer PII exposed through misconfigured bucket.",
        "severity": "critical",
        "status": "open",
        "owner_id": None,
        "assignee_id": None,
        "timeline": [],
        "evidence": {},
        "notes": "",
        "tasks": []
    }
    response = client.post("/api/incidents/", json=incident_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Data Leak Investigation"
    incident_id = data["id"]

    # GET incident
    response_get = client.get(f"/api/incidents/{incident_id}")
    assert response_get.status_code == 200

    # UPDATE incident status
    response_put = client.put(f"/api/incidents/{incident_id}", json={"status": "investigating"})
    assert response_put.status_code == 200
    assert response_put.json()["status"] == "investigating"

    # Append timeline event
    response_time = client.post(f"/api/incidents/{incident_id}/timeline?event_text=Containment%20applied")
    assert response_time.status_code == 200
    assert len(response_time.json()["timeline"]) >= 2

def test_audit_logs():
    # Log an event
    log_audit_event(
        actor="admin",
        action="test_action",
        resource_type="system",
        result="success",
        metadata={"info": "pytest audit event"}
    )
    
    # GET /api/audit-logs
    response = client.get("/api/audit-logs/")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
    assert logs[0]["actor"] == "admin"

def test_notifications(mock_auth_dependencies):
    # Create notification
    notif_payload = {
        "title": "Critical Patch Required",
        "message": "Nginx requires security patch CVE-2023-0001.",
        "type": "cve_alert",
        "is_read": False,
        "user_id": str(mock_auth_dependencies)
    }
    response = client.post("/api/notifications/", json=notif_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Critical Patch Required"
    notif_id = data["id"]

    # List notifications
    response_list = client.get("/api/notifications/")
    assert response_list.status_code == 200
    assert len(response_list.json()) >= 1

    # Mark as read
    response_read = client.put(f"/api/notifications/{notif_id}/read")
    assert response_read.status_code == 200
    assert response_read.json()["is_read"] is True

    # Mark all read
    response_all = client.put("/api/notifications/read-all")
    assert response_all.status_code == 200

def test_system_ai_health():
    # GET /ai-health
    response = client.get("/ai-health")
    assert response.status_code == 200
    data = response.json()
    assert "backend_status" in data
    assert "rasa_status" in data
    assert "gemini_status" in data
    assert "rag_status" in data
    assert "chromadb_document_count" in data
