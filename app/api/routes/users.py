from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles, verify_csrf
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import RefreshResponse
from app.schemas.user import ChangePasswordRequest, UserSummary
from app.services.auth_service import AuthService, InvalidOldPasswordError
from app.services.token_service import (
    build_fingerprint,
    build_refresh_session_expiry,
    create_access_token,
    create_refresh_token,
    parse_device_info,
    persist_refresh_jti,
    revoke_all_user_sessions_and_tokens,
    set_auth_cookies,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/health")
def users_health() -> Dict[str, str]:
    return {"status": "ok", "module": "users"}


@router.get("/me", response_model=UserSummary)
async def me(current_user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.get("/admin/health")
async def admin_health(_: User = Depends(require_roles(ROLE_ADMIN))) -> Dict[str, str]:
    return {"status": "ok", "scope": "admin"}


@router.post("/me/change-password", response_model=RefreshResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password",
        )

    auth_service = AuthService(db)
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            old_password=payload.old_password,
            new_password=payload.new_password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidOldPasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )

    await revoke_all_user_sessions_and_tokens(db=db, user_id=str(current_user.id))

    refresh_jti = str(uuid4())
    device_info = parse_device_info(request.headers.get("user-agent"))
    fingerprint = build_fingerprint(request.client.host if request.client else None)
    access_token = create_access_token(user_id=str(current_user.id), role=current_user.role)
    refresh_token = create_refresh_token(
        user_id=str(current_user.id), role=current_user.role, jti=refresh_jti
    )
    await persist_refresh_jti(
        user_id=str(current_user.id),
        jti=refresh_jti,
        device_info=device_info,
        fingerprint=fingerprint,
    )
    await SessionRepository(db).create_session(
        user_id=current_user.id,
        jti=refresh_jti,
        session_expires_at=build_refresh_session_expiry(),
    )
    set_auth_cookies(response, access_token, refresh_token)
    return RefreshResponse(message="Password changed successfully")
