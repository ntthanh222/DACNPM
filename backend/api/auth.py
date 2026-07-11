"""
JWT Authentication Module for CyberSec Assistant

Provides JWT token generation, validation, and user authentication endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
import uuid
import logging
import re
import os
import bcrypt
import secrets
import unicodedata

logger = logging.getLogger(__name__)

# Module-level cache for JWT secret to ensure consistency
_jwt_secret_cache = None

def _get_jwt_secret():
    global _jwt_secret_cache
    if _jwt_secret_cache is not None:
        return _jwt_secret_cache

    try:
        from config import settings
        val = getattr(settings, 'jwt_secret', None)
        if val and val != "change-this-to-a-secure-random-key-in-production":
            _jwt_secret_cache = val
            return val
    except Exception:
        pass

    env_val = os.getenv("JWT_SECRET")
    if env_val and env_val != "change-this-to-a-secure-random-key-in-production":
        _jwt_secret_cache = env_val
        return env_val

    # Generate once and cache
    _jwt_secret_cache = secrets.token_urlsafe(32)
    logger.warning("Using random JWT secret - configure JWT_SECRET environment variable for production")
    return _jwt_secret_cache

SECRET_KEY = _get_jwt_secret()
ALGORITHM = "HS256"

def _get_token_expire():
    try:
        from config import settings
        val = getattr(settings, 'access_token_expire_minutes', None)
        if val:
            return val
    except Exception:
        pass
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))

ACCESS_TOKEN_EXPIRE_MINUTES = _get_token_expire()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')

        # NEW: Support Vietnamese characters and other Unicode letters
        # Pattern allows: letters (including Unicode), numbers, and ., _, @, +, -
        if not re.match(r'^[\w\u00C0-\u017F\u1EA0-\u1EF9.@+-]+$', v):
            raise ValueError('Username can contain letters (including Vietnamese), numbers, and ., _, @, +, -')

        # Additional security: prevent homograph attacks
        if contains_mixed_scripts(v):
            raise ValueError('Username cannot mix different character scripts')

        return v

    @validator('password')
    def validate_password(cls, v):
        if v and len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v


def contains_mixed_scripts(text: str) -> bool:
    """Detect if text mixes different scripts (potential homograph attack)"""
    scripts = set()
    for char in text:
        if char.isalpha():
            try:
                script = unicodedata.name(char, '').split(' ')[0]
                if script:
                    scripts.add(script)
            except (ValueError, IndexError):
                # If we can't determine the script, be conservative
                scripts.add('UNKNOWN')

    # Allow mixing with Latin script for Vietnamese
    dangerous_mixes = scripts - {'LATIN', 'LATIN_EXTENDED', 'UNKNOWN'}
    return len(dangerous_mixes) > 1


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: Optional[str] = None


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class TokenData(BaseModel):
    """Token data model"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[datetime] = None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData with decoded information

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        username = payload.get("username")

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id, username=username)
        return token_data

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Raises:
        ValueError: If password exceeds bcrypt's 72-byte limit
    """
    # Validate password length before hashing (bcrypt has 72-byte limit)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Bcrypt verification failed: {e}")
        return False


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> TokenData:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. No credentials provided."
        )
    token = credentials.credentials
    token_data = verify_token(token)
    return token_data



async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[TokenData]:
    """
    Dependency to get current user if authenticated, otherwise return None.
    Allows anonymous access.

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        TokenData if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        return verify_token(token)
    except HTTPException:
        return None


def create_user(user_data: UserCreate) -> Dict[str, Any]:
    """
    Create a new user in the database.

    Args:
        user_data: User creation data

    Returns:
        Created user information
    """
    try:
        from backend.database.crud.users import create_user
        from backend.database.models import UserCreate as DBUserCreate

        # Hash password if provided
        hashed_password = None
        if user_data.password:
            hashed_password = hash_password(user_data.password)

        # Create user in database
        db_user = DBUserCreate(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name or user_data.username,
            hashed_password=hashed_password,
            # Registration is a public endpoint: do not rely on a database
            # default that could grant elevated access to new accounts.
            role="user",
            is_active=True,
        )

        created_user = create_user(db_user)

        if not created_user:
            raise HTTPException(
                status_code=400,
                detail="Username already exists or database unavailable"
            )

        return {
            "id": str(created_user.id),
            "username": created_user.username,
            "email": created_user.email,
            "full_name": created_user.full_name
        }

    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=400, detail="Failed to create user")


def authenticate_user(username: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with username and password.

    SECURITY: User must exist in database. No auto-creation allowed.
    Users must register via /api/auth/register endpoint first.

    Args:
        username: Username to authenticate
        password: Password for authentication (required for users with password)

    Returns:
        User data if authentication successful, None otherwise
    """
    try:
        from backend.database.crud.users import get_user_by_email, get_user_by_username

        user = get_user_by_username(username)

        # The login form permits either an application username or an email.
        # Prefer username first so accounts with a literal @ in their username
        # retain their existing sign-in behavior.
        if not user and "@" in username:
            user = get_user_by_email(username)

        # SECURITY FIX: Do NOT auto-create user if not found
        if not user:
            logger.warning(f"Authentication failed: User '{username}' not found")
            return None

        if not user.is_active:
            logger.warning(f"Authentication failed: User '{username}' is inactive")
            return None

        # If user has password set, verify it
        if user.hashed_password:
            if not password:
                logger.warning(f"Authentication failed: Password required for user '{username}'")
                return None
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Authentication failed: Incorrect password for user '{username}'")
                return None
        elif password:
            # User has no password set but password was provided
            logger.warning(f"Authentication failed: User '{username}' has no password set")
            return None

        logger.info(f"User authenticated successfully: {username}")
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name
        }

    except Exception as e:
        logger.error(f"Authentication error for '{username}': {e}")
        return None
