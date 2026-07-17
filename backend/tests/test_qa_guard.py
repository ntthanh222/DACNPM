from __future__ import annotations

import pytest

from testing.scripts.qa_guard import QAGuardError, assert_qa_mutation_allowed


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ALLOW_QA_MUTATIONS", "true")
    monkeypatch.setenv("QA_DATABASE_CONFIRMATION", "ISOLATED_QA_DATABASE")
    monkeypatch.setenv("SUPABASE_URL", "http://local-qa.invalid")
    monkeypatch.setenv("DB_HOST", "localhost")


def test_qa_guard_allows_explicit_isolated_local_qa(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)

    assert_qa_mutation_allowed()


def test_qa_guard_rejects_missing_mutation_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.delenv("ALLOW_QA_MUTATIONS")

    with pytest.raises(QAGuardError, match="ALLOW_QA_MUTATIONS"):
        assert_qa_mutation_allowed()


def test_qa_guard_rejects_known_production_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "https://aivvorhfsxjpfeqpcxxh.supabase.co")

    with pytest.raises(QAGuardError, match="known production"):
        assert_qa_mutation_allowed()


def test_qa_guard_rejects_unmarked_cloud_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_URL", "https://randomproject.supabase.co")

    with pytest.raises(QAGuardError, match="qa/test/staging"):
        assert_qa_mutation_allowed()
