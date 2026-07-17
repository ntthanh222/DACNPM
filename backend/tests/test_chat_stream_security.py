from uuid import uuid4
from pathlib import Path

import pytest

import backend.api.chatbot as chatbot_api
import backend.services.rasa_client as rasa_client_module
from backend.middleware.error_handler import REDACTED_VALUE, _sanitize_query_params
from backend.services.chatbot_service import ChatbotService, SENSITIVE_CHAT_PLACEHOLDER
from backend.services.rasa_client import RasaClient


def test_error_logging_redacts_stream_credentials_from_query_params():
    class FakeQueryParams:
        def items(self):
            return [
                ("message", "hello"),
                ("stream_ticket", "secret-ticket"),
                ("token", "jwt-token"),
            ]

    class FakeRequest:
        query_params = FakeQueryParams()

    assert _sanitize_query_params(FakeRequest()) == {
        "message": "hello",
        "stream_ticket": REDACTED_VALUE,
        "token": REDACTED_VALUE,
    }


def test_rasa_default_fallback_has_local_provider_failure_response():
    source = (Path(__file__).parent.parent / "rasa_actions" / "actions.py").read_text(encoding="utf-8")

    assert "def _local_fallback_response" in source
    assert "Fallback LLM unavailable, using local response" in source
    assert "not _validate_uuid(user_id)" in source
    assert "scan URL" in source
    assert "thu hoi token" in source


def test_gemini_rate_limit_fails_fast_to_fallback():
    source = (Path(__file__).parent.parent / "llm" / "gemini_service.py").read_text(encoding="utf-8")

    assert "Gemini rate limit or quota reached; failing fast to local fallback" in source
    assert "is_rate_limit and attempt < max_retries" not in source


def test_stream_ticket_is_single_use_and_expires(monkeypatch):
    user_id = uuid4()
    monkeypatch.setattr(chatbot_api, "STREAM_TICKET_TTL_SECONDS", 1)
    monkeypatch.setattr(chatbot_api.time, "time", lambda: 1000.0)

    ticket = chatbot_api._issue_stream_ticket(user_id)

    assert chatbot_api._consume_stream_ticket(ticket) == user_id
    assert chatbot_api._consume_stream_ticket(ticket) is None

    expired_ticket = chatbot_api._issue_stream_ticket(user_id)
    monkeypatch.setattr(chatbot_api.time, "time", lambda: 1002.0)

    assert chatbot_api._consume_stream_ticket(expired_ticket) is None


def test_password_chat_messages_are_redacted_before_persistence():
    service = ChatbotService.__new__(ChatbotService)

    assert service._redact_sensitive_message(
        "Evaluate password: CorrectHorse1!",
        {"intent": "password"},
    ) == SENSITIVE_CHAT_PLACEHOLDER
    assert service._redact_sensitive_message(
        "Check this URL https://example.com",
        {"intent": "phishing"},
    ) == "Check this URL https://example.com"


@pytest.mark.asyncio
async def test_rasa_client_joins_multiple_text_messages(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return [
                {"text": "first"},
                {"text": ""},
                {"text": "second"},
                {"image": "ignored"},
            ]

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(rasa_client_module.httpx, "AsyncClient", FakeClient)

    response = await RasaClient().send_message("hello", "user-1")

    assert response == "first\n\nsecond"
