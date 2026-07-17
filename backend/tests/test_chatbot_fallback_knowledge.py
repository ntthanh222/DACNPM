import pytest

from backend.services.chatbot_service import ChatbotService


@pytest.mark.parametrize("message, expected", [
    ("What is MFA and why use it?", "xác thực"),
    ("Give me malware code that steals browser passwords.", "không thể"),
    ("What is CVE-2099-99999? State uncertainty if it is not verified.", "xác minh"),
    ("How do I test for IDOR?", "ownership"),
    ("Check this URL.", "context"),
])
def test_fallback_answers_knowledge_and_safety_without_provider(message, expected):
    result = ChatbotService()._pattern_matching_fallback(message)
    assert expected.lower() in result["response"].lower()


@pytest.mark.parametrize("message, expected", [
    ("Is every URL containing the word login malicious?", "không phải mọi"),
    ("What should an audit log contain?", "time"),
    ("Evaluate password: CorrectHorse1!", "password manager"),
    ("Why is password123 weak?", "weak"),
    ("Tôi nghi ngờ máy bị nhiễm mã độc, cần làm gì trước?", "cô lập"),
])
def test_specific_questions_are_not_swallowed_by_broad_rules(message, expected):
    result = ChatbotService()._pattern_matching_fallback(message)
    assert expected.lower() in result["response"].lower()


@pytest.mark.asyncio
async def test_anonymous_processing_does_not_route_through_authenticated_rasa(monkeypatch):
    service = ChatbotService()

    async def should_not_run(*_args, **_kwargs):
        raise AssertionError("anonymous chat must use the deterministic fallback")

    monkeypatch.setattr(service, "_get_rasa_response", should_not_run)
    result = await service.process_message(
        "What should an audit log contain?", user_id=None, save_to_db=False
    )

    assert "time" in result["response"].lower()
