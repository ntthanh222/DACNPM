"""Backward-compatible authentication facade.

New code should import DTOs from ``backend.application.auth.schemas``,
business operations from ``backend.application.auth.service``, and security
helpers from ``backend.core.security``.
"""

from backend.application.auth.schemas import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    contains_mixed_scripts,
)
from backend.application.auth.service import authenticate_user, create_user
from backend.core.security import (
    ALGORITHM,
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    security,
    verify_password,
    verify_token,
)

__all__ = [
    "UserCreate", "UserLogin", "Token", "TokenData", "contains_mixed_scripts",
    "create_access_token", "verify_token", "hash_password", "verify_password",
    "get_current_user", "get_optional_user", "create_user", "authenticate_user",
    "security", "ALGORITHM",
]
