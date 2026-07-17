"""Shared fail-closed guard for QA scripts that can mutate data."""
from __future__ import annotations

import os
from urllib.parse import urlparse


KNOWN_PRODUCTION_SUPABASE_REFS = {"aivvorhfsxjpfeqpcxxh"}
ALLOWED_ENVIRONMENTS = {"test", "qa"}


class QAGuardError(RuntimeError):
    """Raised when QA mutation safety requirements are not satisfied."""


def _contains_known_prod_ref(value: str) -> bool:
    return any(ref in value for ref in KNOWN_PRODUCTION_SUPABASE_REFS)


def assert_qa_mutation_allowed() -> None:
    """Require explicit isolated-QA intent before running mutating scripts."""
    environment = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise QAGuardError("ENVIRONMENT or APP_ENV must be test or qa for QA mutations.")

    if os.getenv("ALLOW_QA_MUTATIONS", "").lower() != "true":
        raise QAGuardError("ALLOW_QA_MUTATIONS=true is required for QA mutations.")

    if os.getenv("QA_DATABASE_CONFIRMATION") != "ISOLATED_QA_DATABASE":
        raise QAGuardError("QA_DATABASE_CONFIRMATION=ISOLATED_QA_DATABASE is required.")

    checked_values = [
        os.getenv("SUPABASE_URL", ""),
        os.getenv("DB_HOST", ""),
        os.getenv("DATABASE_URL", ""),
        os.getenv("POSTGRES_DSN", ""),
    ]
    if any(_contains_known_prod_ref(value) for value in checked_values):
        raise QAGuardError("Refusing to mutate known production Supabase database.")

    supabase_url = os.getenv("SUPABASE_URL", "")
    parsed = urlparse(supabase_url)
    if parsed.hostname and parsed.hostname.endswith(".supabase.co"):
        hostname = parsed.hostname.lower()
        if not any(marker in hostname for marker in ("qa", "test", "staging")):
            raise QAGuardError("Cloud Supabase mutations require a qa/test/staging project URL.")


def guard_or_exit() -> None:
    try:
        assert_qa_mutation_allowed()
    except QAGuardError as exc:
        print(f"Refusing QA mutation: {exc}")
        raise SystemExit(2) from exc
