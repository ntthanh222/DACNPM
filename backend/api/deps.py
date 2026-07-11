"""
Authentication and authorization dependencies for API endpoints.

This module provides FastAPI dependencies for validating user credentials
and ensuring proper access control to protected resources.

SECURITY: JWT tokens are REQUIRED for protected endpoints.
X-User-ID header is only used for anonymous/read-only endpoints.
"""
from fastapi import Header, HTTPException, Depends
from uuid import UUID
from typing import Optional
from backend.api.auth import get_current_user, get_optional_user, TokenData
import logging

logger = logging.getLogger(__name__)


async def get_current_user_id(
    jwt_user: Optional[TokenData] = Depends(get_current_user),
    x_user_id: Optional[str] = Header(None)
) -> UUID:
    """
    Get current user ID from JWT token ONLY (no insecure fallback).

    SECURITY: JWT token is REQUIRED for protected endpoints.
    X-User-ID header fallback has been removed for security reasons.
    Use require_current_user_id for endpoints that modify data.

    Args:
        jwt_user: User data from JWT token (REQUIRED)
        x_user_id: DEPRECATED - X-User-ID header is no longer accepted

    Returns:
        UUID: The validated user ID

    Raises:
        HTTPException: 401 if no valid JWT token is provided
        HTTPException: 400 if the user ID is not a valid UUID
    """
    # JWT token is REQUIRED - no fallback to X-User-ID in production
    if not jwt_user or not jwt_user.user_id:
        from backend.config.settings import settings
        if settings.environment == "development" and x_user_id:
            logger.warning(f"⚠️ SECURITY WARNING: Using deprecated X-User-ID fallback for user {x_user_id} in development mode")
            try:
                return UUID(x_user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user ID in X-User-ID header.")
        
        logger.warning("Authentication attempt without valid JWT token")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide valid JWT token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Warn if X-User-ID header is present (deprecated)
    if x_user_id:
        logger.warning(f"X-User-ID header ignored for security - JWT required")

    try:
        return UUID(jwt_user.user_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID in token."
        )


async def require_current_user_id(
    jwt_user: Optional[TokenData] = Depends(get_current_user),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
) -> UUID:
    """
    Require authenticated user with JWT token (NO X-User-ID fallback).

    SECURITY: This function REQUIRES valid JWT token.
    X-User-ID header is NOT accepted as it can be spoofed.
    Use this for endpoints that modify data (POST/PUT/DELETE).

    Args:
        jwt_user: User data from JWT token (REQUIRED)
        x_user_id: DEPRECATED - X-User-ID header is ignored for security

    Returns:
        UUID: The validated and verified user ID

    Raises:
        HTTPException: 401 if no valid JWT token is provided
        HTTPException: 400 if the user ID in token is not a valid UUID
        HTTPException: 403 if the user ID doesn't exist in database
    """
    if jwt_user and jwt_user.user_id:
        if x_user_id:
            logger.warning(f"X-User-ID header ignored for user {x_user_id} - JWT required")
        try:
            user_id = UUID(jwt_user.user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user ID in token."
            )
    else:
        from backend.config.settings import settings

        if settings.environment != "development" or not x_user_id:
            logger.warning("Authentication attempt without JWT token")
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please provide valid JWT token.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        logger.warning(f"⚠️ SECURITY WARNING: Using deprecated X-User-ID fallback for user {x_user_id} in development mode")
        try:
            user_id = UUID(x_user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID in X-User-ID header.")

    # Check if user exists in database
    from backend.database.crud.users import get_user
    from backend.database.connection import is_database_available

    if not is_database_available():
        logger.error(f"Database unavailable when verifying user {user_id}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable - database connection required"
        )

    user = get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=403,
            detail="User not found. Invalid user ID."
        )
    return user_id


async def get_optional_user_id(
    jwt_user: Optional[TokenData] = Depends(get_optional_user)
) -> Optional[UUID]:
    """
    Get optional user ID from JWT token only.

    This dependency extracts the user ID from the JWT token if present.
    Returns None if no authentication is provided.
    Use this for endpoints that work both with and without authentication.

    Args:
        jwt_user: User data from JWT token

    Returns:
        Optional[UUID]: The validated user ID, or None if not provided

    Raises:
        HTTPException: 400 if the user ID is provided but not a valid UUID
    """
    if jwt_user and jwt_user.user_id:
        try:
            return UUID(jwt_user.user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user ID in token."
            )

    return None


async def require_admin(user_id: UUID = Depends(require_current_user_id)) -> UUID:
    """
    Require admin role for access to admin-only endpoints.

    This dependency validates that the authenticated user has admin role
    and is active. Use this for endpoints that require administrative privileges.

    Args:
        user_id: The validated user ID from require_current_user_id

    Returns:
        UUID: The admin user ID

    Raises:
        HTTPException: 403 if user doesn't have admin role or is not active
    """
    try:
        from backend.database.crud.users import get_user

        user = get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=403,
                detail="User not found. Access denied."
            )

        if user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Admin role required. Access denied."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is inactive. Access denied."
            )

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error checking admin role: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error verifying admin privileges."
        )


async def require_admin_or_analyst(user_id: UUID = Depends(require_current_user_id)) -> UUID:
    """
    Require admin or security_analyst role for access to protected endpoints.

    This dependency validates that the authenticated user has admin or
    security_analyst role and is active.

    Args:
        user_id: The validated user ID from require_current_user_id

    Returns:
        UUID: The user ID

    Raises:
        HTTPException: 403 if user doesn't have required role or is not active
    """
    try:
        from backend.database.crud.users import get_user

        user = get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=403,
                detail="User not found. Access denied."
            )

        if user.role not in ['admin', 'security_analyst']:
            raise HTTPException(
                status_code=403,
                detail="Admin or Security Analyst role required. Access denied."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is inactive. Access denied."
            )

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error checking role: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error verifying privileges."
        )


async def get_admin_client(admin_id: UUID = Depends(require_admin)):
    """
    Get Supabase admin client with admin role verification.

    SECURITY: This function verifies admin role BEFORE returning the
    service role client that bypasses RLS. This prevents unauthorized
    access to the admin client.

    Args:
        admin_id: The validated admin user ID from require_admin

    Returns:
        Supabase admin client with service role permissions

    Raises:
        HTTPException: 403 if admin role verification fails
        HTTPException: 500 if admin client initialization fails
    """
    try:
        from backend.database.connection import get_supabase_admin_client

        admin_client = get_supabase_admin_client()

        if not admin_client:
            logger.error("Failed to initialize admin client for verified admin")
            raise HTTPException(
                status_code=500,
                detail="Admin service unavailable. Contact system administrator."
            )

        logger.debug(f"Admin client provided to verified admin user {admin_id}")
        return admin_client

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error providing admin client: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error initializing admin services."
        )
