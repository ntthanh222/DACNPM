from datetime import datetime, timezone
from uuid import uuid4

from backend.database.models import User
from backend.repositories import users


class _Query:
    def __init__(self, owner):
        self.owner = owner

    def select(self, _columns):
        return self

    def eq(self, _column, _value):
        return self

    def execute(self):
        return self.owner.execute()


class _Client:
    def __init__(self, execute):
        self.execute = execute

    def table(self, _name):
        return _Query(self)


def test_user_lookup_reconnects_after_transient_postgrest_disconnect(monkeypatch):
    now = datetime.now(timezone.utc)
    payload = {
        "id": str(uuid4()),
        "username": "qa-transient",
        "email": "qa-transient@example.test",
        "full_name": "Transient QA",
        "role": "user",
        "is_active": True,
        "password_hash": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    calls = {"old": 0, "new": 0}

    def old_execute():
        calls["old"] += 1
        raise ConnectionError("Server disconnected")

    def new_execute():
        calls["new"] += 1
        return type("Response", (), {"data": [payload]})()

    monkeypatch.setattr(users, "supabase_admin", _Client(old_execute))
    monkeypatch.setattr(users, "get_supabase_admin_client", lambda: _Client(new_execute))
    monkeypatch.setattr(users, "supabase", None)

    result = users.get_user_by_username("qa-transient", use_cache=False)

    assert isinstance(result, User)
    assert result.username == "qa-transient"
    assert calls == {"old": 1, "new": 1}
