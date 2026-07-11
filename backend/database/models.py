from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import re

# ============================================================================
# USER MODELS (Enhanced replacement for Profile)
# ============================================================================

class UserBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[\w\u00C0-\u017F\u1EA0-\u1EF9.@+-]+$")
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = Field(default="user", pattern="^(user|admin|security_analyst)$")
    is_active: bool = True
    security_context: Optional[Dict[str, Any]] = None
    # Field name kept as hashed_password for code clarity; DB column is password_hash.
    # The alias makes model_dump(by_alias=True) emit "password_hash" for PostgREST.
    hashed_password: Optional[str] = Field(default=None, alias="password_hash")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

class UserCreate(UserBase):
    id: Optional[UUID] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(user|admin|security_analyst)$")
    is_active: Optional[bool] = None
    security_context: Optional[Dict[str, Any]] = None
    last_security_scan: Optional[datetime] = None

class User(UserBase):
    id: UUID
    last_security_scan: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# PROFILE MODELS (Legacy - kept for backward compatibility)
# ============================================================================

class ProfileBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileCreate(ProfileBase):
    id: Optional[UUID] = None

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class Profile(ProfileBase):
    id: UUID
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatHistoryBase(BaseModel):
    user_message: str
    bot_response: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None

class ChatHistoryCreate(ChatHistoryBase):
    user_id: UUID

class ChatHistory(ChatHistoryBase):
    id: Optional[UUID] = None  # Make Optional for offline mode
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SecurityNewsBase(BaseModel):
    title: str
    url: str
    source: str
    description: Optional[str] = None
    published_at: Optional[datetime] = None

class SecurityNewsCreate(SecurityNewsBase):
    pass

class SecurityNewsUpdate(BaseModel):
    """Model for updating security news items - all fields optional"""
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None

class SecurityNews(SecurityNewsBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityStats(BaseModel):
    """Vulnerability distribution statistics"""
    injection: int
    cross_site_scripting: int
    authentication: int
    remote_code_execution: int
    memory_corruption: int
    csrf: int
    other: int
    total: int
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemHealth(BaseModel):
    """System health metrics"""
    database_status: str
    database_latency_ms: Optional[float]
    rasa_status: str
    timestamp: float


# ============================================================================
# SECURITY SCAN MODELS
# ============================================================================

class SecurityScanBase(BaseModel):
    scan_type: str = Field(..., pattern="^(url_scan|password_check|vulnerability_scan)$")
    target: str = Field(..., min_length=1)
    scan_result: Optional[Dict[str, Any]] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    severity: Optional[str] = Field(None, pattern="^(info|low|medium|high|critical)$")
    status: str = Field(default="pending", pattern="^(pending|completed|failed)$")
    scan_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @field_validator('target')
    @classmethod
    def validate_target(cls, v, info):
        scan_type = info.data.get('scan_type', '')
        if scan_type == 'url_scan':
            if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v):
                raise ValueError('Invalid URL format')
        elif scan_type == 'password_check':
            if len(v) < 1:
                raise ValueError('Password cannot be empty')
        return v

class SecurityScanCreate(SecurityScanBase):
    user_id: UUID
    scan_timestamp: Optional[datetime] = None

class SecurityScanUpdate(BaseModel):
    scan_result: Optional[Dict[str, Any]] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    severity: Optional[str] = Field(None, pattern="^(info|low|medium|high|critical)$")
    status: Optional[str] = Field(None, pattern="^(pending|completed|failed)$")
    scan_metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class SecurityScan(SecurityScanBase):
    id: UUID
    user_id: UUID
    scan_timestamp: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CVE LOOKUP MODELS
# ============================================================================

class CVELookupBase(BaseModel):
    cve_id: str = Field(..., pattern=r'^CVE-\d{4}-\d{4,}$')
    query_data: Dict[str, Any] = Field(default_factory=dict)
    response_data: Dict[str, Any] = Field(default_factory=dict)
    cvss_score: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(none|low|medium|high|critical)$")

    @field_validator('cve_id')
    @classmethod
    def validate_cve_id(cls, v):
        if not re.match(r'^CVE-\d{4}-\d{4,}$', v.upper()):
            raise ValueError('Invalid CVE ID format. Expected: CVE-YYYY-NNNN')
        return v.upper()

class CVELookupCreate(CVELookupBase):
    cache_expires_at: datetime
    query_count: int = Field(default=1, ge=1)

class CVELookupUpdate(BaseModel):
    response_data: Optional[Dict[str, Any]] = None
    cvss_score: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(none|low|medium|high|critical)$")
    cache_expires_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

class CVELookup(CVELookupBase):
    id: UUID
    query_timestamp: datetime
    cache_expires_at: datetime
    query_count: int
    last_accessed: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CACHE STATISTICS MODELS
# ============================================================================

class CacheStatistics(BaseModel):
    """CVE cache statistics for monitoring and analytics"""
    total_entries: int
    active_entries: int
    expired_entries: int
    avg_query_count: float
    most_accessed_cve: Optional[str]
    cache_hit_rate: float

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SCAN STATISTICS MODELS
# ============================================================================

class ScanStatistics(BaseModel):
    """Security scan statistics for user dashboard"""
    total_scans: int
    completed_scans: int
    failed_scans: int
    pending_scans: int
    high_risk_scans: int
    critical_risk_scans: int
    avg_risk_score: float
    last_scan_timestamp: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
