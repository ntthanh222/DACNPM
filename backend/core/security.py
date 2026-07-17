"""JWT and password security helpers."""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import InvalidTokenError as JWTError

from backend.application.auth.schemas import TokenData
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
_jwt_secret_cache: Optional[str] = None


def _get_jwt_secret() -> str:
    """
    Retrieves the JWT secret key from the application settings or environment.
    If none is configured or if the default insecure key is present, a secure random 
    secret is generated and cached for the duration of the server runtime.

    Returns:
        str: The secret key used for signing and verifying JWTs.
    """
    global _jwt_secret_cache
    if _jwt_secret_cache:
        return _jwt_secret_cache
    configured = getattr(get_settings(), "jwt_secret", None) or os.getenv("JWT_SECRET")
    if configured and configured != "change-this-to-a-secure-random-key-in-production":
        _jwt_secret_cache = configured
    else:
        # Fallback to randomly generated secret to prevent insecure defaults in development
        _jwt_secret_cache = secrets.token_urlsafe(32)
        logger.warning("Using random JWT secret; configure JWT_SECRET for production")
    return _jwt_secret_cache


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JWT access token containing the provided claims.

    Args:
        data (Dict[str, Any]): Dictionary of claims to include in the JWT payload.
        expires_delta (Optional[timedelta], optional): Custom expiration duration. If omitted,
            uses the configured default expiration from settings.

    Returns:
        str: Encoded and signed JWT token.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=get_settings().access_token_expire_minutes))
    payload["exp"] = expire
    return jwt.encode(payload, _get_jwt_secret(), algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    """
    Decodes and validates a JWT token.

    Args:
        token (str): The raw signed JWT access token.

    Raises:
        HTTPException: 401 Unauthorized if the token is invalid, expired, or missing 'sub'.

    Returns:
        TokenData: Decoded claims mapped to a TokenData schema.
    """
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
    """
    Hashes a plaintext password using Bcrypt with a randomly generated salt.

    Args:
        password (str): Plaintext password to hash.

    Raises:
        ValueError: If password exceeds the maximum allowed bcrypt length (72 bytes).

    Returns:
        str: The UTF-8 decoded bcrypt password hash string.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.

    Args:
        plain_password (str): Plaintext password.
        hashed_password (str): Stored bcrypt hash.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.error("Bcrypt verification failed: %s", exc)
        return False


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> TokenData:
    """
    FastAPI dependency that extracts and validates the Bearer token from the Request headers.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Autopopulated from the HTTPBearer scheme.

    Raises:
        HTTPException: 401 Unauthorized if the credentials are not provided or are invalid.

    Returns:
        TokenData: The validated token payload.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. No credentials provided.")
    return verify_token(credentials.credentials)


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[TokenData]:
    """
    FastAPI dependency that attempts to extract and validate the Bearer token from Request headers,
    but does not raise an exception if it is missing or invalid.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): Autopopulated from the HTTPBearer scheme.

    Returns:
        Optional[TokenData]: The validated token payload if valid, otherwise None.
    """
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
