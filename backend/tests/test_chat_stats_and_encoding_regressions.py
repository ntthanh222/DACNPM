"""Regression tests for user chat statistics and Unicode chat payloads."""

from uuid import UUID, uuid4

import pytest

from backend.api.stats import get_chat_statistics_endpoint
import backend.api.stats as stats_api


def test_chat_statistics_are_scoped_to_the_authenticated_user(monkeypatch):
    captured = {}

    def fake_get_chat_statistics(limit=1000, user_id=None):
        captured.update(limit=limit, user_id=user_id)
        return {"total_conversations": 0}

    monkeypatch.setattr(stats_api, "get_chat_statistics", fake_get_chat_statistics)

    current_user_id = uuid4()
    result = get_chat_statistics_endpoint(limit=25, current_user_id=current_user_id)

    assert result == {"total_conversations": 0}
    assert captured == {"limit": 25, "user_id": str(current_user_id)}


def test_unicode_chat_payload_is_preserved_by_the_create_model():
    from backend.database.models import ChatHistoryCreate

    message = "CVE-2024-3094 là gì? 🔐"
    chat = ChatHistoryCreate(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        user_message=message,
        bot_response="Trả lời tiếng Việt",
    )

    assert chat.user_message == message
    assert chat.bot_response == "Trả lời tiếng Việt"
