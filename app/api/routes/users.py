import csv
import io
import json
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles, verify_csrf
from app.core.constants import ROLE_ADMIN
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import RefreshResponse
from app.schemas.user import (
    ChangePasswordRequest,
    SecurityEventListResponse,
    SecurityEventSummary,
    UserSummary,
)
from app.services.auth_service import AuthService, InvalidOldPasswordError
from app.services.alert_service import emit_security_alert
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


@router.get("/admin/security-events", response_model=SecurityEventListResponse)
async def admin_security_events(
    limit: int = Query(default=50, ge=1, le=500),
    severity: Optional[str] = Query(default=None, pattern="^(low|medium|high|critical)$"),
    alert_type: Optional[str] = Query(default=None, min_length=2, max_length=100),
    _: User = Depends(require_roles(ROLE_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> SecurityEventListResponse:
    events = await AuditRepository(db).list_security_events(
        limit=limit,
        severity=severity,
        alert_type=alert_type,
    )
    rows = [
        SecurityEventSummary(
            id=str(item.id),
            created_at=item.created_at.isoformat(),
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
