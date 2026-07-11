"""
Authentication Routes for CyberSec Assistant

Provides login and register endpoints for JWT-based authentication.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from backend.api.auth import (
    UserCreate,
    UserLogin,
    Token,
    create_access_token,
    authenticate_user,
    create_user
)
from backend.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    message: str


class RegisterResponse(BaseModel):
    """Registration response model"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    message: str


@router.post("/login", response_model=LoginResponse, tags=["authentication"])
def login(user_login: UserLogin):
    """
    Login endpoint to authenticate user and return JWT token.

    User must exist in database. Use /api/auth/register to create new users.
    """
    try:
        user = authenticate_user(user_login.username, user_login.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user["id"], "username": user["username"]}
        )

        logger.info(f"User logged in: {user['username']}")

        return LoginResponse(
            access_token=access_token,
            user_id=user["id"],
            username=user["username"],
            message="Login successful"
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Import error in login endpoint: {e}")
        raise HTTPException(status_code=500, detail="Server configuration error")
    except AttributeError as e:
        logger.error(f"Attribute error in login endpoint: {e}")
        raise HTTPException(status_code=500, detail="Database unavailable - try again later")
    except Exception as e:
        logger.error(f"Unexpected login error for {user_login.username}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@router.post("/register", response_model=RegisterResponse, tags=["authentication"])
def register(user_data: UserCreate):
    """
    Register endpoint to create a new user and return JWT token.

    SECURITY FIX: Reject duplicate usernames instead of auto-login.
    """
    try:
        # Check if username already exists (WITHOUT password authentication)
        from backend.database.crud.users import get_user_by_username, get_user_by_email

        existing_user = get_user_by_username(user_data.username)

        if existing_user:
            # SECURITY: Reject duplicate registration - do NOT auto-login
            logger.warning(f"Registration attempt with existing username: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác hoặc đăng nhập bằng tài khoản hiện có."
            )

        # Check if email already exists (DB enforces UNIQUE on email column)
        if user_data.email:
            existing_email = get_user_by_email(user_data.email)
            if existing_email:
                logger.warning(f"Registration attempt with existing email: {user_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email đã được sử dụng. Vui lòng dùng email khác hoặc đăng nhập."
                )

        # Create new user
        new_user = create_user(user_data)

        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể tạo tài khoản. Vui lòng thử lại sau."
            )

        # Create JWT token
        access_token = create_access_token(
            data={"sub": new_user["id"], "username": new_user["username"]}
        )

        logger.info(f"New user registered: {new_user['username']}")

        return RegisterResponse(
            access_token=access_token,
            user_id=new_user["id"],
            username=new_user["username"],
            message="Registration successful"
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Validation/constraint errors (e.g. from create_user): surface a useful message
        logger.warning(f"Registration validation error: {e}")
        msg = str(e)
        if 'already exists' in msg.lower():
            detail = "Tên đăng nhập hoặc email đã tồn tại."
        elif 'database unavailable' in msg.lower():
            detail = "Hệ thống đang bận, vui lòng thử lại sau."
        else:
            detail = "Dữ liệu đăng ký không hợp lệ."
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        logger.error(f"Registration error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Đăng ký thất bại. Vui lòng thử lại.")


@router.post("/verify-token", response_model=Dict[str, Any], tags=["authentication"])
def verify_token_endpoint(token: str):
    """
    Verify a JWT token and return user information.

    Useful for frontend to check if token is still valid.
    """
    try:
        from backend.api.auth import verify_token
        token_data = verify_token(token)

        return {
            "valid": True,
            "user_id": token_data.user_id,
            "username": token_data.username
        }

    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@router.get("/me", response_model=Dict[str, Any], tags=["authentication"])
def get_current_user_info(
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get current user information including role.

    Returns the full user profile for the authenticated user.
    """
    try:
        from uuid import UUID as UUIDType
        from backend.database.crud.users import get_user
        from backend.database.connection import is_database_available

        # Check database availability
        if not is_database_available():
            logger.warning(f"Database unavailable when fetching user {user_id}")
            raise HTTPException(
                status_code=503,
                detail="Database temporarily unavailable. Please try again later."
            )

        user = get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_security_scan": user.last_security_scan.isoformat() if user.last_security_scan else None
        }

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Import error in /me endpoint: {e}")
        raise HTTPException(status_code=500, detail="Server configuration error")
    except AttributeError as e:
        logger.error(f"Attribute error in /me endpoint: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable - try again later")
    except Exception as e:
        logger.error(f"Error getting user info for {user_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")
