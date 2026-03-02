from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser, RefreshResponse
from app.services.token_service import (
    TokenValidationError,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    verify_refresh_token,
)
from app.services.auth_service import AuthService, InactiveUserError, InvalidCredentialsError
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health")
def auth_health() -> Dict[str, str]:
    return {"status": "ok", "module": "auth"}


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    auth_service = AuthService(db)

    try:
        user = await auth_service.login(
            email_or_username=payload.email_or_username,
            password=payload.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    refresh_token = create_refresh_token(user_id=str(user.id), role=user.role)
    set_auth_cookies(response, access_token, refresh_token)

    return LoginResponse(
        message="Login successful",
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            is_verified=user.is_verified,
        ),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = verify_refresh_token(refresh_token)
    except TokenValidationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await UserRepository(db).get_by_id_with_relationships(user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    new_refresh_token = create_refresh_token(user_id=str(user.id), role=user.role)
    set_auth_cookies(response, access_token, new_refresh_token)
    return RefreshResponse(message="Token refresh successful")


@router.post("/logout", response_model=RefreshResponse)
def logout(response: Response) -> RefreshResponse:
    clear_auth_cookies(response)
    return RefreshResponse(message="Logout successful")
