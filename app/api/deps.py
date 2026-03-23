from uuid import UUID
from typing import Callable, Optional, Set

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.token_service import TokenValidationError, verify_access_token


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


def require_access_cookie(
    access_token: Optional[str] = Cookie(
        default=None,
        alias=settings.ACCESS_COOKIE_NAME,
        description="Required HttpOnly access token cookie for authenticated routes.",
    ),
) -> str:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )
    return access_token


def require_refresh_cookie(
    refresh_token: Optional[str] = Cookie(
        default=None,
        alias=settings.REFRESH_COOKIE_NAME,
        description="Required HttpOnly refresh token cookie for refresh/logout endpoints.",
    ),
) -> str:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    return refresh_token


def optional_refresh_cookie(
    refresh_token: Optional[str] = Cookie(
        default=None,
        alias=settings.REFRESH_COOKIE_NAME,
        description="Optional HttpOnly refresh token cookie. If present, session is revoked on logout.",
    ),
) -> Optional[str]:
    return refresh_token


async def verify_csrf(
    request: Request,
    csrf_cookie: Optional[str] = Cookie(
        default=None,
        alias=settings.CSRF_COOKIE_NAME,
        description="Required CSRF cookie for state-changing operations.",
    ),
    csrf_header: Optional[str] = Header(default=None, alias=settings.CSRF_HEADER_NAME),
) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


async def get_current_user(
    request: Request,
    access_token: str = Depends(require_access_cookie),
    db: AsyncSession = Depends(get_db),
) -> User:
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
    "optional_refresh_cookie",
    "require_access_cookie",
    "require_refresh_cookie",
    "require_roles",
    "verify_csrf",
]
