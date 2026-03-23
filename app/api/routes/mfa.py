from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.mfa import MFASetupResponse, MFAVerifyRequest, MFAVerifyResponse
from app.services.totp_service import build_provisioning_uri, generate_totp_secret, verify_totp_code
from app.utils.encryption import EncryptionError, decrypt_text, encrypt_text


router = APIRouter(prefix="/mfa", tags=["mfa"])


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
    try:
        decrypted_secret = decrypt_text(current_user.totp_secret)
    except EncryptionError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA secret state")
    if not verify_totp_code(secret=decrypted_secret, code=payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")

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
