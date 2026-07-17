from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.notifications import create_notification
from backend.database.models import NotificationCreate


@pytest.mark.asyncio
async def test_create_notification_rejects_foreign_user_id() -> None:
    current_user_id = uuid4()
    other_user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await create_notification(
            NotificationCreate(
                user_id=other_user_id,
                title="forged",
                message="should not be accepted",
                type="qa",
            ),
            user_id=current_user_id,
        )

    assert exc_info.value.status_code == 403
