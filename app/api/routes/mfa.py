from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.constants import SUPPORTED_MFA_TYPES
from app.core.database import get_db
from app.models.user import User
from app.models.user_mfa import UserMFA
from app.repositories.audit_repository import AuditRepository
from app.schemas.mfa import (
    MFAEmailSetupResponse,
    MFAEmailVerifyRequest,
    MFAOptionsResponse,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
)
from app.services.mfa_email_service import send_email_mfa_setup_code, verify_email_mfa_setup_code
from app.services.totp_service import build_provisioning_uri, generate_totp_secret, verify_totp_code
from app.utils.encryption import decrypt_text, encrypt_text, is_encrypted_text


router = APIRouter(prefix="/mfa", tags=["mfa"])


def _enabled_mfa_methods(user: User) -> list[str]:
    methods: list[str] = []
    if user.totp_secret and user.mfa_enabled:
        methods.append("totp")

    for item in user.mfa_methods:
        if item.mfa_type == "email" and item.is_enabled:
            methods.append("email")
            break

    return sorted(set(methods))


@router.get("/options", response_model=MFAOptionsResponse)
async def get_mfa_options(current_user: User = Depends(get_current_user)) -> MFAOptionsResponse:
    return MFAOptionsResponse(
        available_methods=sorted(SUPPORTED_MFA_TYPES),
        enabled_methods=_enabled_mfa_methods(current_user),
    )


@router.post("/setup", response_model=MFASetupResponse)
async def setup_totp(
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFASetupResponse:
    secret = generate_totp_secret()
    provisioning_uri = build_provisioning_uri(secret=secret, email=current_user.email)
    current_user.totp_secret = encrypt_text(secret)
    current_user.mfa_enabled = False
    await db.commit()

    await AuditRepository(db).create_event(
        user_id=current_user.id,
        event_type="MFA_SETUP_INITIATED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={},
    )
    return MFASetupResponse(secret=secret, provisioning_uri=provisioning_uri)


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_totp_setup(
    payload: MFAVerifyRequest,
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFAVerifyResponse:
    if not current_user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA setup not initiated")

    secret = decrypt_text(current_user.totp_secret)
    if not verify_totp_code(secret=secret, code=payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")

    if not is_encrypted_text(current_user.totp_secret):
        current_user.totp_secret = encrypt_text(secret)
    current_user.mfa_enabled = True
    await db.commit()
    await AuditRepository(db).create_event(
        user_id=current_user.id,
        event_type="MFA_ENABLED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={},
    )
    return MFAVerifyResponse(message="MFA enabled successfully")


@router.post("/setup/email", response_model=MFAEmailSetupResponse)
async def setup_email_mfa(
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFAEmailSetupResponse:
    expires_in = await send_email_mfa_setup_code(user_id=current_user.id, to_email=current_user.email)

    await AuditRepository(db).create_event(
        user_id=current_user.id,
        event_type="MFA_EMAIL_SETUP_INITIATED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={},
    )
    return MFAEmailSetupResponse(
        message="Email MFA setup code sent",
        expires_in_seconds=expires_in,
    )


@router.post("/verify/email", response_model=MFAVerifyResponse)
async def verify_email_mfa_setup(
    payload: MFAEmailVerifyRequest,
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFAVerifyResponse:
    is_valid = await verify_email_mfa_setup_code(user_id=current_user.id, code=payload.code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")

    existing = next(
        (item for item in current_user.mfa_methods if item.mfa_type == "email"),
        None,
    )
    if existing:
        existing.is_enabled = True
    else:
        db.add(
            UserMFA(
                user_id=current_user.id,
                mfa_type="email",
                secret_encrypted=encrypt_text("email_mfa_enabled"),
                is_enabled=True,
            )
        )

    current_user.mfa_enabled = True
    await db.commit()
    await AuditRepository(db).create_event(
        user_id=current_user.id,
        event_type="MFA_EMAIL_ENABLED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={},
    )
    return MFAVerifyResponse(message="Email MFA enabled successfully")
