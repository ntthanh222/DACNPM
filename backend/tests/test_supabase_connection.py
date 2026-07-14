"""Regression tests for Supabase API-key client configuration."""

from pathlib import Path
import sys
from types import SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_new_supabase_api_keys_do_not_use_bearer_authorization():
    """Modern sb_* keys must be sent through the apikey header only."""
    from backend.database.connection import _create_supabase_client

    client = _create_supabase_client(
        "https://example.supabase.co", "sb_publishable_test"
    )

    assert client.postgrest.headers.get("apikey") == "sb_publishable_test"
    assert client.postgrest.headers.get("authorization") is None


def test_legacy_supabase_api_keys_keep_bearer_authorization():
    """Legacy JWT keys retain the library's existing authorization behavior."""
    from backend.database.connection import _create_supabase_client

    client = _create_supabase_client("https://example.supabase.co", "legacy-key")

    assert client.postgrest.headers.get("authorization") == "Bearer legacy-key"


def test_authentication_accepts_the_account_email(monkeypatch):
    """Users may sign in with their email when the username is not known."""
    from backend.api import auth
    from backend.repositories import users

    account = SimpleNamespace(
        id="user-1",
        username="admin",
        email="admin@cybersec.local",
        full_name="System Administrator",
        hashed_password=auth.hash_password("StrongPass123"),
        is_active=True,
    )
    monkeypatch.setattr(users, "get_user_by_username", lambda identifier: None)
    monkeypatch.setattr(
        users,
        "get_user_by_email",
        lambda identifier: account if identifier == account.email else None,
    )

    authenticated = auth.authenticate_user(account.email, "StrongPass123")

    assert authenticated == {
        "id": "user-1",
        "username": "admin",
        "email": "admin@cybersec.local",
        "full_name": "System Administrator",
    }


def test_authentication_rejects_inactive_accounts(monkeypatch):
    """Disabled accounts must never receive a valid login response."""
    from backend.api import auth
    from backend.repositories import users

    account = SimpleNamespace(
        id="user-2",
        username="disabled_user",
        email="disabled@example.com",
        full_name="Disabled User",
        hashed_password=auth.hash_password("StrongPass123"),
        is_active=False,
    )
    monkeypatch.setattr(
        users,
        "get_user_by_username",
        lambda identifier: account if identifier == account.username else None,
    )

    assert auth.authenticate_user(account.username, "StrongPass123") is None


def test_registration_explicitly_persists_standard_user_role(monkeypatch):
    """The database must not choose an elevated role for a public registration."""
    from backend.api import auth
    from backend.repositories import users

    persisted_payload = {}

    def persist_user(user):
        persisted_payload.update(user.model_dump(exclude_unset=True, by_alias=True))
        return SimpleNamespace(
            id="user-3",
            username=user.username,
            email=user.email,
            full_name=user.full_name,
        )

    monkeypatch.setattr(users, "create_user", persist_user)

    auth.create_user(
        auth.UserCreate(
            username="new_user",
            email="new@example.com",
            full_name="New User",
            password="StrongPass123",
        )
    )

    assert persisted_payload["role"] == "user"
    assert persisted_payload["is_active"] is True
