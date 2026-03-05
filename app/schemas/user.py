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
