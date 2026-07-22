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
    
    # Mock Rasa NLU to return a basic intent
    async def mock_get_intent(*args, **kwargs):
        return {"intent": "greet", "confidence": 0.99, "entities": []}
    monkeypatch.setattr(service.rasa_client, "get_intent", mock_get_intent)

    # Mock Rasa Action to return a response
    async def mock_send_message(*args, **kwargs):
        return "Chào bạn!"
    monkeypatch.setattr(service.rasa_client, "send_message", mock_send_message)

    # Ensure database saving is NOT called
    saved = []
    def mock_save(*args, **kwargs):
        saved.append(args)
    monkeypatch.setattr(service, "_save_chat_message", mock_save)

    result = await service.process_message(
        "Xin chào", user_id=None, persist=True
    )

    assert "chào" in result["response"].lower()
    assert len(saved) == 0  # No database save occurred for anonymous user
