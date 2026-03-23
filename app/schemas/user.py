from pydantic import BaseModel, Field
from typing import List


class UserSummary(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class SessionSummary(BaseModel):
    jti: str
    session_started_at: str
    session_expires_at: str
    is_revoked: bool
    is_current: bool


class SessionsListResponse(BaseModel):
    sessions: List[SessionSummary]
