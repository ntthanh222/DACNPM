import pytest

from backend.utils import cve_lookup


def test_cve_validation_sync_lookup_and_parser(monkeypatch):
    class Response:
        status_code = 200
        def json(self): return {"vulnerabilities": [{"cve": {"descriptions": [{"lang": "en", "value": "desc"}], "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}]}, "references": [{"url": "https://ref"}], "configurations": [{"nodes": [{"cpeMatch": [{"vulnerable": True, "criteria": "cpe:one"}]}]}]}}]}
    monkeypatch.setattr(cve_lookup.requests, "get", lambda *_args, **_kwargs: Response())
    assert cve_lookup.validate_cve_id("cve-2024-1234") is True
    assert cve_lookup.lookup_cve("2024-1234")["vulnerabilities"]
    parsed = cve_lookup.check_cve("CVE-2024-1234")
    assert parsed["severity"] == "critical"
    assert parsed["response_data"]["affected_products"] == ["cpe:one"]
    assert cve_lookup.lookup_cve("bad")["fallback"] is True


@pytest.mark.asyncio
async def test_async_check_cve_uses_mocked_lookup(monkeypatch):
    async def lookup(_cve): return {"vulnerabilities": []}
    monkeypatch.setattr(cve_lookup, "async_lookup_cve", lookup)
    result = await cve_lookup.async_check_cve("CVE-2024-1234")
    assert result["error"] == "CVE not found"
