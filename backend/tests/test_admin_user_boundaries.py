from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api import deps
from backend.api.v1.admin import user_management


class FakeResponse:
    def __init__(self, data=None):
        self.data = data or []


class FakeTable:
    def __init__(self, client, name):
        self.client = client
        self.name = name
        self.filters = {}
        self.update_payload = None
        self.insert_payload = None

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def execute(self):
        if self.name == "users" and self.update_payload is not None:
            user_id = self.filters.get("id")
            self.client.updates.append((user_id, self.update_payload))
            return FakeResponse([{**self.update_payload, "id": user_id}])
        if self.name == "users":
            role = self.filters.get("role")
            is_active = self.filters.get("is_active")
            data = [
                {"id": str(user.id), "role": user.role, "is_active": user.is_active}
                for user in self.client.users.values()
                if (role is None or user.role == role) and (is_active is None or user.is_active == is_active)
            ]
            return FakeResponse(data)
        if self.name == "admin_audit_log":
            self.client.audit_log.append(self.insert_payload)
            return FakeResponse([self.insert_payload])
        return FakeResponse([])


class FakeAdminClient:
    def __init__(self, users):
        self.users = users
        self.updates = []
        self.audit_log = []

    def table(self, name):
        return FakeTable(self, name)


def make_user(user_id, role, is_active=True, username="qa_user"):
    return SimpleNamespace(id=user_id, role=role, is_active=is_active, username=username)


@pytest.mark.asyncio
async def test_require_current_user_id_rejects_inactive_user(monkeypatch):
    inactive_id = uuid4()
    token = SimpleNamespace(user_id=str(inactive_id))
    monkeypatch.setattr("backend.repositories.users.get_user", lambda _: make_user(inactive_id, "user", False))

    with pytest.raises(HTTPException) as error:
        await deps.require_current_user_id(jwt_user=token, x_user_id=None)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_grant_super_admin(monkeypatch):
    admin_id = uuid4()
    target_id = uuid4()
    users = {
        admin_id: make_user(admin_id, "admin", True, "qa_admin"),
        target_id: make_user(target_id, "user", True, "qa_user_a"),
    }
    monkeypatch.setattr(user_management, "get_user", lambda user_id: users.get(user_id))
    client = FakeAdminClient(users)

    with pytest.raises(HTTPException) as error:
        await user_management.update_user_role(
            target_id,
            user_management.UserRoleUpdate(role="super_admin"),
            admin_id=admin_id,
            admin_client=client,
        )

    assert error.value.status_code == 403
    assert client.updates == []


@pytest.mark.asyncio
async def test_admin_cannot_disable_super_admin(monkeypatch):
    admin_id = uuid4()
    super_admin_id = uuid4()
    users = {
        admin_id: make_user(admin_id, "admin", True, "qa_admin"),
        super_admin_id: make_user(super_admin_id, "super_admin", True, "qa_superadmin"),
    }
    monkeypatch.setattr(user_management, "get_user", lambda user_id: users.get(user_id))
    client = FakeAdminClient(users)

    with pytest.raises(HTTPException) as error:
        await user_management.update_user_status(
            super_admin_id,
            user_management.UserStatusUpdate(is_active=False),
            admin_id=admin_id,
            admin_client=client,
        )

    assert error.value.status_code == 403
    assert client.updates == []


@pytest.mark.asyncio
async def test_last_super_admin_cannot_be_demoted(monkeypatch):
    super_admin_id = uuid4()
    users = {
        super_admin_id: make_user(super_admin_id, "super_admin", True, "qa_superadmin"),
    }
    monkeypatch.setattr(user_management, "get_user", lambda user_id: users.get(user_id))
    client = FakeAdminClient(users)

    with pytest.raises(HTTPException) as error:
        await user_management.update_user_role(
            super_admin_id,
            user_management.UserRoleUpdate(role="admin"),
            admin_id=super_admin_id,
            admin_client=client,
        )

    assert error.value.status_code == 400
    assert client.updates == []
