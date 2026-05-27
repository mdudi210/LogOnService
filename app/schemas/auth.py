from typing import Literal, Optional

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
    user: Optional[LoginUser] = None
    mfa_required: bool = False
    mfa_token: Optional[str] = None
    mfa_methods: Optional[list[str]] = None


class RefreshResponse(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=255)


class RegisterResponse(BaseModel):
    message: str
    user: LoginUser


class LoginMFARequest(BaseModel):
    mfa_token: str
    method: Literal["totp", "email"] = "totp"
    code: str = Field(min_length=6, max_length=8)


class OAuthLinkRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=50)
    provider_user_id: str = Field(min_length=2, max_length=255)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class OAuthLoginRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=50)
    provider_user_id: str = Field(min_length=2, max_length=255)


class OAuthProviderResponse(BaseModel):
    providers: list[str]


class OAuthGoogleAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthGoogleCallbackResponse(BaseModel):
    message: str
    user: LoginUser
