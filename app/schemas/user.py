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
    user_id: Optional[str] = None
    alert_type: str
    severity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict


class SecurityEventListResponse(BaseModel):
    count: int
    events: list[SecurityEventSummary]
