from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email_or_username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class LoginUser(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_verified: bool


class LoginResponse(BaseModel):
    message: str
    user: LoginUser
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "bearer"
