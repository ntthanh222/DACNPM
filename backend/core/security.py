"""JWT and password security helpers."""

import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from backend.application.auth.schemas import TokenData
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
_jwt_secret_cache: Optional[str] = None


def _get_jwt_secret() -> str:
    global _jwt_secret_cache
    if _jwt_secret_cache:
        return _jwt_secret_cache
    configured = getattr(get_settings(), "jwt_secret", None) or os.getenv("JWT_SECRET")
    if configured and configured != "change-this-to-a-secure-random-key-in-production":
        _jwt_secret_cache = configured
    else:
        _jwt_secret_cache = secrets.token_urlsafe(32)
        logger.warning("Using random JWT secret; configure JWT_SECRET for production")
    return _jwt_secret_cache


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=get_settings().access_token_expire_minutes))
    payload["exp"] = expire
    return jwt.encode(payload, _get_jwt_secret(), algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return TokenData(user_id=user_id, username=payload.get("username"))
    except JWTError as exc:
        logger.warning("JWT decode error: %s", exc)
        raise credentials_exception from exc


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.error("Bcrypt verification failed: %s", exc)
        return False


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> TokenData:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. No credentials provided.")
    return verify_token(credentials.credentials)


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[TokenData]:
    if credentials is None:
        return None
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


__all__ = [
    "ALGORITHM", "security", "create_access_token", "verify_token", "hash_password",
    "verify_password", "get_current_user", "get_optional_user",
]
