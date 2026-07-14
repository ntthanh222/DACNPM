"""Authentication request, response, and token DTOs."""

import re
import unicodedata
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


def contains_mixed_scripts(text: str) -> bool:
    scripts = set()
    for char in text:
        if char.isalpha():
            scripts.add(unicodedata.name(char, "UNKNOWN").split(" ")[0])
    return len(scripts - {"LATIN", "LATIN_EXTENDED", "UNKNOWN"}) > 1


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not re.match(r"^[\w\u00C0-\u017F\u1EA0-\u1EF9.@+-]+$", value):
            raise ValueError("Username can contain letters (including Vietnamese), numbers, and ., _, @, +, -")
        if contains_mixed_scripts(value):
            raise ValueError("Username cannot mix different character scripts")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value.encode("utf-8")) > 72:
            raise ValueError("Password cannot be longer than 72 characters")
        return value


class UserLogin(BaseModel):
    username: str
    password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[datetime] = None


__all__ = ["UserCreate", "UserLogin", "Token", "TokenData", "contains_mixed_scripts"]
