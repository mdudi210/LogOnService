import csv
import io
import json
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_refresh_token, require_roles, verify_csrf
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RefreshResponse
from app.schemas.user import (
    AdminUserAuthListResponse,
    AdminUserAuthSummary,
    ActivityEventListResponse,
    ActivityEventSummary,
    ChangePasswordRequest,
    SecurityEventListResponse,
    SecurityEventSummary,
    SessionListResponse,
    SessionSummary,
    UserSummary,
)
from app.services.alert_service import emit_security_alert
from app.services.auth_service import AuthService, InvalidOldPasswordError
from app.services.token_service import (
    build_fingerprint,
    build_refresh_session_expiry,
    create_access_token,
    create_refresh_token,
    parse_device_info,
    persist_refresh_jti,
    revoke_all_user_sessions_and_tokens,
    revoke_jti,
    set_auth_cookies,
    verify_refresh_token,
)

router = APIRouter(prefix="/users", tags=["users"])


async def _audit_best_effort(
    *,
    db: AsyncSession,
    user_id: UUID,
    event_type: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: dict,
) -> None:
    try:
        await AuditRepository(db).create_event(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    except Exception:
        # Observability should not break auth/session control paths.
        return


def _enabled_mfa_methods(user: User) -> list[str]:
    methods: list[str] = []
    if getattr(user, "totp_secret", None) and bool(getattr(user, "mfa_enabled", False)):
        methods.append("totp")
    for item in getattr(user, "mfa_methods", []) or []:
        if item.mfa_type == "email" and item.is_enabled:
            methods.append("email")
    return sorted(set(methods))


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


@router.get("/me/sessions", response_model=SessionListResponse)
async def list_my_sessions(
    current_user: User = Depends(get_current_user),
    refresh_token: str = Depends(get_refresh_token),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    payload = verify_refresh_token(refresh_token)
    current_jti = payload["jti"]

    sessions = await SessionRepository(db).get_active_sessions(current_user.id)
    rows = [
        SessionSummary(
            jti=item.jti,
            session_started_at=item.session_started_at.isoformat(),
            session_expires_at=item.session_expires_at.isoformat(),
            is_revoked=item.is_revoked,
            is_current=item.jti == current_jti,
        )
        for item in sessions
    ]
    return SessionListResponse(count=len(rows), sessions=rows)


@router.delete("/me/sessions/{jti}", response_model=RefreshResponse)
async def revoke_my_session(
    jti: str,
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    session = await SessionRepository(db).get_by_jti(jti)
    if session is None or str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await revoke_jti(user_id=str(current_user.id), jti=jti)
    await SessionRepository(db).revoke_session_by_jti(jti)
    await _audit_best_effort(
        db=db,
        user_id=current_user.id,
        event_type="SESSION_REVOKED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"jti": jti},
    )
    return RefreshResponse(message="Session revoked successfully")


@router.delete("/me/sessions", response_model=RefreshResponse)
async def revoke_other_sessions(
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    refresh_token: str = Depends(get_refresh_token),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    payload = verify_refresh_token(refresh_token)
    current_jti = payload["jti"]

    revoked_jtis = await SessionRepository(db).revoke_other_sessions(
        user_id=current_user.id,
        exclude_jti=current_jti,
    )
    for item_jti in revoked_jtis:
        await revoke_jti(user_id=str(current_user.id), jti=item_jti)

    await _audit_best_effort(
        db=db,
        user_id=current_user.id,
        event_type="OTHER_SESSIONS_REVOKED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"revoked_count": len(revoked_jtis)},
    )
    return RefreshResponse(message="Other sessions revoked successfully")


@router.get("/admin/health")
async def admin_health(_: User = Depends(require_roles(ROLE_ADMIN))) -> Dict[str, str]:
    return {"status": "ok", "scope": "admin"}


@router.get("/admin/users", response_model=AdminUserAuthListResponse)
async def admin_users_auth_overview(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AdminUserAuthListResponse:
    users = await UserRepository(db).list_for_admin_auth_view(limit=limit, offset=offset)
    rows = [
        AdminUserAuthSummary(
            id=str(item.id),
            email=item.email,
            username=item.username,
            role=item.role,
            is_active=item.is_active,
            is_verified=item.is_verified,
            mfa_enabled=item.mfa_enabled,
            enabled_mfa_methods=_enabled_mfa_methods(item),
            oauth_providers=sorted([account.provider for account in item.oauth_accounts]),
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )
        for item in users
    ]
    return AdminUserAuthListResponse(count=len(rows), users=rows)


@router.get("/admin/security-events", response_model=SecurityEventListResponse)
async def admin_security_events(
    limit: int = Query(default=50, ge=1, le=500),
    event_type: Optional[str] = Query(default=None, min_length=2, max_length=100),
    severity: Optional[str] = Query(default=None, pattern="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(default=None, min_length=2, max_length=100),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SecurityEventListResponse:
    if event_type:
        events = await AuditRepository(db).list_recent_events(
            limit=limit,
            event_types=[event_type],
        )
    else:
        events = await AuditRepository(db).list_security_events(
            limit=limit,
            severity=severity,
            alert_type=alert_type,
        )

    rows = [
        SecurityEventSummary(
            id=str(item.id),
            created_at=item.created_at.isoformat(),
            event_type=item.event_type,
            user_id=str(item.user_id) if item.user_id else None,
            alert_type=item.event_metadata.get("alert_type", "unknown"),
            severity=item.event_metadata.get("severity", "unknown"),
            ip_address=item.ip_address,
            user_agent=item.user_agent,
            metadata=item.event_metadata,
        )
        for item in events
    ]
    return SecurityEventListResponse(count=len(rows), events=rows)


@router.get("/admin/security-events/export")
async def export_security_events_csv(
    limit: int = Query(default=500, ge=1, le=5000),
    severity: Optional[str] = Query(default=None, pattern="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(default=None, min_length=2, max_length=100),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    events = await AuditRepository(db).list_security_events(
        limit=limit,
        severity=severity,
        alert_type=alert_type,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "event_id",
            "created_at",
            "event_type",
            "user_id",
            "alert_type",
            "severity",
            "ip_address",
            "user_agent",
            "metadata_json",
        ]
    )

    for item in events:
        metadata = item.event_metadata or {}
        writer.writerow(
            [
                str(item.id),
                item.created_at.isoformat(),
                item.event_type,
                str(item.user_id) if item.user_id else "",
                metadata.get("alert_type", "unknown"),
                metadata.get("severity", "unknown"),
                item.ip_address or "",
                item.user_agent or "",
                json.dumps(metadata, default=str),
            ]
        )

    output.seek(0)
    filename = f"security-events-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/activity", response_model=ActivityEventListResponse)
async def admin_activity_events(
    limit: int = Query(default=100, ge=1, le=1000),
    event_type: Optional[str] = Query(default=None, min_length=2, max_length=100),
    user_id: Optional[str] = Query(default=None, min_length=36, max_length=36),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ActivityEventListResponse:
    parsed_user_id: Optional[UUID] = None
    if user_id:
        try:
            parsed_user_id = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")

    events = await AuditRepository(db).list_recent_events(
        limit=limit,
        event_types=[event_type] if event_type else None,
        user_id=parsed_user_id,
    )
    rows = [
        ActivityEventSummary(
            id=str(item.id),
            created_at=item.created_at.isoformat(),
            event_type=item.event_type,
            user_id=str(item.user_id) if item.user_id else None,
            ip_address=item.ip_address,
            user_agent=item.user_agent,
            metadata=item.event_metadata or {},
        )
        for item in events
    ]
    return ActivityEventListResponse(count=len(rows), events=rows)


@router.post("/admin/security-events/test-alert", response_model=RefreshResponse)
async def emit_test_security_alert(
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    await emit_security_alert(
        db=db,
        alert_type="MANUAL_TEST_ALERT",
        severity="low",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"source": "admin_test_endpoint"},
    )
    return RefreshResponse(message="Test alert emitted")


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
