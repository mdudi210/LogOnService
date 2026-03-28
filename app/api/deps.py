from uuid import UUID
from typing import Callable, Optional, Set

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyCookie, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenValidationError, verify_access_token


access_token_cookie = APIKeyCookie(
    name=settings.ACCESS_COOKIE_NAME,
    auto_error=False,
    scheme_name="AccessTokenCookie",
)
refresh_token_cookie = APIKeyCookie(
    name=settings.REFRESH_COOKIE_NAME,
    auto_error=False,
    scheme_name="RefreshTokenCookie",
)
csrf_cookie = APIKeyCookie(
    name=settings.CSRF_COOKIE_NAME,
    auto_error=False,
    scheme_name="CsrfCookie",
)
csrf_header = APIKeyHeader(
    name=settings.CSRF_HEADER_NAME,
    auto_error=False,
    scheme_name="CsrfHeader",
)


def _get_access_payload_or_401(request: Request) -> dict:
    access_token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    try:
        return verify_access_token(access_token)
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )


async def verify_csrf(
    request: Request,
    csrf_cookie_value: Optional[str] = Security(csrf_cookie),
    csrf_header_value: Optional[str] = Security(csrf_header),
) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    if (
        not csrf_cookie_value
        or not csrf_header_value
        or csrf_cookie_value != csrf_header_value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Optional[str] = Security(access_token_cookie),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    try:
        payload = verify_access_token(access_token)
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    try:
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user = await UserRepository(db).get_by_id_with_relationships(user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    if user.role != payload.get("role"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    return user


async def get_refresh_token(refresh_token: Optional[str] = Security(refresh_token_cookie)) -> str:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    return refresh_token


def require_roles(*allowed_roles: str) -> Callable:
    normalized_roles: Set[str] = {role.strip().lower() for role in allowed_roles if role.strip()}

    async def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = (current_user.role or "").strip().lower()
        if user_role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if ROLE_ADMIN in normalized_roles and user_role == ROLE_ADMIN:
            payload = _get_access_payload_or_401(request)
            if not payload.get("mfa_authenticated"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="MFA is required for admin access",
                )
        return current_user

    return dependency


__all__ = [
    "get_db",
    "get_current_user",
    "get_refresh_token",
    "require_roles",
    "verify_csrf",
]
