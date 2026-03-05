from uuid import UUID
from typing import Callable, Set

from fastapi import Depends, HTTPException, Request, status
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


async def verify_csrf(request: Request) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(settings.CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    payload = _get_access_payload_or_401(request)

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


__all__ = ["get_db", "get_current_user", "require_roles", "verify_csrf"]
