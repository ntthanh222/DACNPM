import sys
import types

from backend.utils import cve_translator


def test_translator_handles_empty_cache_and_success(monkeypatch):
    cve_translator.clear_translation_cache()
    assert cve_translator.translate_cve_description("", "CVE-1") == "Không có mô tả"
    service = types.SimpleNamespace(generate_response=lambda **_kwargs: "Bản dịch")
    module = types.SimpleNamespace(get_gemini_service_singleton=lambda: service)
    monkeypatch.setitem(sys.modules, "backend.llm.gemini_service", module)
    assert cve_translator.translate_cve_description("English", "CVE-2024-1", "9.8", "critical") == "Bản dịch"
    assert cve_translator.translate_cve_description("English", "CVE-2024-1") == "Bản dịch"


def test_translate_cve_response_updates_description_and_preserves_invalid_data(monkeypatch):
    monkeypatch.setattr(cve_translator, "translate_cve_description", lambda *_args: "Vietnamese")
    payload = {"response_data": {"description": "English"}, "cvss_score": "5", "severity": "medium"}
    result = cve_translator.translate_cve_response(payload, "CVE-2024-1")
    assert result["translated"] is True
    assert result["response_data"]["description_original"] == "English"
    assert cve_translator.translate_cve_response({}, "CVE") == {}
