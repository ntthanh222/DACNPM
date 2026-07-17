"""Authentication business operations."""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException

from backend.application.auth.schemas import UserCreate
from backend.core.security import hash_password, verify_password
from backend.database.models import UserCreate as DBUserCreate

logger = logging.getLogger(__name__)


def create_user(user_data: UserCreate) -> Dict[str, Any]:
    from backend.repositories.users import create_user as persist_user

    try:
        db_user = DBUserCreate(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or user_data.username,
            hashed_password=hash_password(user_data.password) if user_data.password else None,
            role="user",
            is_active=True,
        )
        created_user = persist_user(db_user)
        if not created_user:
            raise HTTPException(status_code=400, detail="Username already exists or database unavailable")
        return {
            "id": str(created_user.id),
            "username": created_user.username,
            "email": created_user.email,
            "full_name": created_user.full_name,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create user: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to create user") from exc


def authenticate_user(username: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from backend.repositories.users import get_user_by_email, get_user_by_username

    try:
        # Always read the latest record during authentication. A cached user
        # may contain an old password hash after an admin reset it externally.
        try:
            user = get_user_by_username(username, use_cache=False)
        except TypeError as exc:
            # Keep compatibility with lightweight test doubles and older
            # repository adapters that still accept one positional argument.
            if "use_cache" not in str(exc):
                raise
            user = get_user_by_username(username)
        if not user and "@" in username:
            user = get_user_by_email(username)
        if not user or not user.is_active:
            logger.warning("Authentication failed for %s", username)
            return None
        if user.hashed_password and (not password or not verify_password(password, user.hashed_password)):
            logger.warning("Authentication failed for %s", username)
            return None
        if not user.hashed_password and password:
            return None
        return {"id": str(user.id), "username": user.username, "email": user.email, "full_name": user.full_name}
    except Exception as exc:
        logger.error("Authentication error for %s: %s", username, exc)
        return None


__all__ = ["create_user", "authenticate_user"]
