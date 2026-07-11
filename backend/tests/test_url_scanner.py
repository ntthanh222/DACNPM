import pytest

from backend.utils import url_scanner
from backend.utils.circuit_breaker import CircuitBreakerOpenError


class Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class AsyncClientStub:
    def __init__(self, get_response, post_response=None, **_kwargs):
        self.get_response = get_response
        self.post_response = post_response
        self.post_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return self.get_response

    async def post(self, *_args, **_kwargs):
        self.post_calls += 1
        return self.post_response


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "https://10.0.0.1",
        "http://[::1]/",
        "https://localhost.localdomain",
        "file:///etc/passwd",
        "example.com",
    ],
)
def test_validate_url_rejects_private_local_and_invalid_urls(url):
    assert url_scanner.validate_url(url) is False


@pytest.mark.parametrize("url", ["https://example.com", "http://public.example/path"])
def test_validate_url_accepts_public_http_urls(url):
    assert url_scanner.validate_url(url) is True


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_uses_fallback_without_an_api_key(monkeypatch):
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "")

    result = await url_scanner.scan_url_virustotal_async("https://example.com")

    assert result["fallback"] is True
    assert result["error"] == "VirusTotal API key not configured"


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_rejects_unsafe_urls_before_an_api_request(monkeypatch):
    async def bypass_circuit_breaker(function):
        return await function()

    monkeypatch.setattr(url_scanner, "call_virustotal", bypass_circuit_breaker)

    result = await url_scanner.scan_url_virustotal_async("http://127.0.0.1")

    assert result["fallback"] is True
    assert result["error"] == "Invalid URL format or security check failed"


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_returns_existing_report_without_posting(monkeypatch):
    report = {"data": {"attributes": {"last_analysis_stats": {"harmless": 5, "malicious": 0}}}}
    client = AsyncClientStub(Response(200, report))

    async def bypass_circuit_breaker(function):
        return await function()

    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")
    monkeypatch.setattr(url_scanner, "call_virustotal", bypass_circuit_breaker)
    monkeypatch.setattr(url_scanner.httpx, "AsyncClient", lambda **kwargs: client)

    result = await url_scanner.scan_url_virustotal_async("https://example.com")

    assert result == report
    assert client.post_calls == 0


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_falls_back_when_submission_fails(monkeypatch):
    client = AsyncClientStub(Response(404), Response(503))

    async def bypass_circuit_breaker(function):
        return await function()

    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")
    monkeypatch.setattr(url_scanner, "call_virustotal", bypass_circuit_breaker)
    monkeypatch.setattr(url_scanner.httpx, "AsyncClient", lambda **kwargs: client)

    result = await url_scanner.scan_url_virustotal_async("https://example.com")

    assert result["fallback"] is True
    assert result["error"] == "API error: 503"
    assert client.post_calls == 1


def test_url_scanner_parses_reports_and_applies_basic_fallback_patterns():
    parsed = url_scanner.parse_virustotal_results(
        {"data": {"attributes": {"last_analysis_stats": {"malicious": 2, "suspicious": 1, "harmless": 7, "undetected": 0}, "last_analysis_date": 123}}},
        "https://example.com",
    )
    assert parsed["risk_level"] == "MEDIUM"
    assert parsed["risk_score"] == 30
    fallback = url_scanner.basic_phishing_check("https://login.example.com/secure")
    assert fallback["risk_level"] == "MEDIUM"


def test_url_scanner_sync_and_async_entrypoints_parse_and_fallback(monkeypatch):
    monkeypatch.setattr(url_scanner, "scan_url_virustotal", lambda _url: {"error": "offline", "message": "offline"})
    assert url_scanner.check_phishing_url("https://login.example.com")["scan_source"] == "pattern_matching"

    async def report(_url, _timeout=10):
        return {"data": {"attributes": {"stats": {"malicious": 0, "suspicious": 0, "harmless": 1, "undetected": 0}}}}
    monkeypatch.setattr(url_scanner, "scan_url_virustotal_async", report)
    import asyncio
    assert asyncio.run(url_scanner.check_phishing_url_async("https://example.com"))["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_returns_report_after_submitting_and_polling(monkeypatch):
    report = {"data": {"attributes": {"last_analysis_stats": {"harmless": 4, "malicious": 1}}}}

    class PollingClient:
        def __init__(self):
            self.get_responses = iter([Response(404), Response(200, report)])
            self.post_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return next(self.get_responses)

        async def post(self, *_args, **_kwargs):
            self.post_calls += 1
            return Response(201)

    async def bypass_circuit_breaker(function):
        return await function()

    async def skip_poll_delay(_seconds):
        return None

    client = PollingClient()
    monkeypatch.setattr(url_scanner, "VIRUSTOTAL_API_KEY", "test-key")
    monkeypatch.setattr(url_scanner, "call_virustotal", bypass_circuit_breaker)
    monkeypatch.setattr(url_scanner.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(url_scanner.asyncio, "sleep", skip_poll_delay)

    result = await url_scanner.scan_url_virustotal_async("https://example.com")

    assert result == report
    assert client.post_calls == 1


@pytest.mark.asyncio
async def test_scan_url_virustotal_async_returns_open_circuit_fallback(monkeypatch):
    async def open_circuit(_function):
        raise CircuitBreakerOpenError("VirusTotal", 60)

    monkeypatch.setattr(url_scanner, "call_virustotal", open_circuit)

    result = await url_scanner.scan_url_virustotal_async("https://example.com")

    assert result["fallback"] is True
    assert result["circuit_breaker_open"] is True
