from typing import Optional

from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class SecurityEventSummary(BaseModel):
    id: str
    created_at: str
    event_type: str
    user_id: Optional[str] = None
    alert_type: str
    severity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict


class SecurityEventListResponse(BaseModel):
    count: int
    events: list[SecurityEventSummary]


class SessionSummary(BaseModel):
    jti: str
    session_started_at: str
    session_expires_at: str
    is_revoked: bool
    is_current: bool = False


class SessionListResponse(BaseModel):
    count: int
    sessions: list[SessionSummary]


class ActivityEventSummary(BaseModel):
    id: str
    created_at: str
    event_type: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict


class ActivityEventListResponse(BaseModel):
    count: int
    events: list[ActivityEventSummary]


class AdminUserAuthSummary(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    enabled_mfa_methods: list[str]
    oauth_providers: list[str]
    created_at: str
    updated_at: str


class AdminUserAuthListResponse(BaseModel):
    count: int
    users: list[AdminUserAuthSummary]
