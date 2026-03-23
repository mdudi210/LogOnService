from typing import Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    require_refresh_cookie,
    require_roles,
    verify_csrf,
)
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.auth import RefreshResponse
from app.schemas.audit import AuditEventSummary, AuditEventsResponse
from app.schemas.user import ChangePasswordRequest, SessionSummary, SessionsListResponse, UserSummary
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
    TokenValidationError,
    revoke_jti,
    verify_refresh_token,
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


@router.get("/admin/security-events", response_model=AuditEventsResponse)
async def admin_security_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str = Query(default=""),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AuditEventsResponse:
    event_types = [event_type] if event_type else None
    events = await AuditRepository(db).list_recent_events(limit=limit, event_types=event_types)
    payload = [
        AuditEventSummary(
            id=str(event.id),
            user_id=str(event.user_id) if event.user_id else None,
            event_type=event.event_type,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            metadata=event.event_metadata,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]
    return AuditEventsResponse(events=payload)


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


@router.get("/me/sessions", response_model=SessionsListResponse)
async def list_my_sessions(
    refresh_token: str = Depends(require_refresh_cookie),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionsListResponse:
    try:
        refresh_payload = verify_refresh_token(refresh_token)
        current_session_jti = refresh_payload["jti"]
    except (TokenValidationError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    sessions = await SessionRepository(db).get_active_sessions(current_user.id)
    payload = [
        SessionSummary(
            jti=session.jti,
            session_started_at=session.session_started_at.isoformat(),
            session_expires_at=session.session_expires_at.isoformat(),
            is_revoked=session.is_revoked,
            is_current=session.jti == current_session_jti,
        )
        for session in sessions
    ]
    return SessionsListResponse(sessions=payload)


@router.delete("/me/sessions/{jti}", response_model=RefreshResponse)
async def revoke_my_session(
    jti: str,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    repo = SessionRepository(db)
    session = await repo.get_by_jti(jti)
    if session is None or str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await revoke_jti(user_id=str(current_user.id), jti=jti)
    await repo.revoke_session_by_jti(jti)
    return RefreshResponse(message="Session revoked successfully")


@router.delete("/me/sessions", response_model=RefreshResponse)
async def revoke_other_sessions(
    refresh_token: str = Depends(require_refresh_cookie),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    try:
        refresh_payload = verify_refresh_token(refresh_token)
        current_jti = refresh_payload["jti"]
        if str(refresh_payload.get("sub")) != str(current_user.id):
            raise TokenValidationError("Refresh token subject mismatch")
    except (TokenValidationError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    repo = SessionRepository(db)
    revoked_jtis = await repo.revoke_other_sessions(
        user_id=current_user.id,
        exclude_jti=current_jti,
    )
    for revoked_jti in revoked_jtis:
        await revoke_jti(user_id=str(current_user.id), jti=revoked_jti)

    return RefreshResponse(message="Other sessions revoked successfully")
