import hashlib

import httpx
import pytest

from backend.utils import password_checker
from backend.utils.circuit_breaker import CircuitBreaker


class AsyncResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class AsyncClientStub:
    def __init__(self, response=None, error=None, **_kwargs):
        self.response = response
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.response


@pytest.fixture(autouse=True)
def reset_hibp_breaker(monkeypatch):
    breaker = CircuitBreaker("test-hibp", failure_threshold=5, timeout=60)
    monkeypatch.setattr(password_checker, "hibp_circuit_breaker", breaker)


def test_calculate_password_entropy_identifies_charset_and_strength():
    weak = password_checker.calculate_password_entropy("aaaa")
    strong = password_checker.calculate_password_entropy("CorrectHorse1!")

    assert weak["charset_size"] == 26
    assert weak["strength"] == "very_weak"
    assert strong["charset_size"] == 94
    assert strong["entropy"] > weak["entropy"]
    assert strong["has_upper"] is True
    assert strong["has_lower"] is True
    assert strong["has_digit"] is True
    assert strong["has_special"] is True


def test_calculate_password_entropy_returns_empty_password_guidance():
    result = password_checker.calculate_password_entropy("")

    assert result["entropy"] == 0
    assert result["strength"] == "very_weak"
    assert result["recommendations"]


@pytest.mark.asyncio
async def test_check_haveibeenpwned_detects_a_breached_password(monkeypatch):
    password = "pwned-password"
    suffix = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()[5:]
    response = AsyncResponse(200, f"{suffix}:42\r\nOTHER:1")
    monkeypatch.setattr(password_checker.httpx, "AsyncClient", lambda **kwargs: AsyncClientStub(response, **kwargs))

    result = await password_checker.check_haveibeenpwned(password)

    assert result["breached"] is True
    assert result["count"] == 42


@pytest.mark.asyncio
async def test_check_haveibeenpwned_reports_unbreached_password(monkeypatch):
    monkeypatch.setattr(
        password_checker.httpx,
        "AsyncClient",
        lambda **kwargs: AsyncClientStub(AsyncResponse(200, "NOT_THE_HASH:1"), **kwargs),
    )

    result = await password_checker.check_haveibeenpwned("unique-password")

    assert result["breached"] is False
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_check_haveibeenpwned_fails_fast_when_its_circuit_is_open(monkeypatch):
    breaker = CircuitBreaker("test-hibp", failure_threshold=1, timeout=60)
    monkeypatch.setattr(password_checker, "hibp_circuit_breaker", breaker)
    monkeypatch.setattr(
        password_checker.httpx,
        "AsyncClient",
        lambda **kwargs: AsyncClientStub(error=httpx.TimeoutException("timeout"), **kwargs),
    )

    await password_checker.check_haveibeenpwned("first")
    result = await password_checker.check_haveibeenpwned("second")

    assert result["service_unavailable"] is True
    assert result["circuit_breaker_active"] is True


def test_check_haveibeenpwned_sync_uses_a_mocked_range_response(monkeypatch):
    import requests

    password = "sync-password"
    suffix = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()[5:]

    class Response:
        status_code = 200
        text = f"{suffix}:7\n"

    monkeypatch.setattr(requests, "get", lambda *_args, **_kwargs: Response())

    result = password_checker.check_haveibeenpwned_sync(password)

    assert result["breached"] is True
    assert result["count"] == 7


def test_check_password_strength_includes_breach_warning_when_password_is_known(monkeypatch):
    monkeypatch.setattr(
        password_checker,
        "check_haveibeenpwned_sync",
        lambda _password: {"breached": True, "count": 9, "message": "breached"},
    )

    result = password_checker.check_password_strength("StrongPassword1!")

    assert result["breached_count"] == 9
    assert result["feedback"][0] == "breached"
    assert result["scan_source"] == "entropy_check+breached_check"


@pytest.mark.asyncio
async def test_check_password_strength_async_combines_entropy_and_mocked_breach_status(monkeypatch):
    async def unbreached(_password):
        return {"breached": False, "count": 0, "message": "not breached"}

    monkeypatch.setattr(password_checker, "check_haveibeenpwned", unbreached)

    result = await password_checker.check_password_strength_async("StrongPassword1!")

    assert result["password_length"] == len("StrongPassword1!")
    assert result["breached_count"] is None
    assert result["scan_source"] == "entropy_check"


def test_format_password_response_supports_api_and_chat_output():
    result = {
        "password_length": 12,
        "strength": "MẠNH",
        "strength_score": 80,
        "crack_time": "< 1 year",
        "has_upper": True,
        "has_lower": True,
        "has_digit": True,
        "has_special": True,
        "breached_count": 3,
        "feedback": ["Use a longer passphrase"],
    }

    assert password_checker.format_password_response(result) == str(result)
    chat_response = password_checker.format_password_response(result, for_chat=True)
    assert "80/100" in chat_response
    assert "3" in chat_response
    assert "Use a longer passphrase" in chat_response
