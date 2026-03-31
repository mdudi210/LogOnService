import re
from typing import Dict, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_refresh_token, verify_csrf
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.oauth_repository import OAuthRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_device_repository import UserDeviceRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginMFARequest,
    LoginRequest,
    LoginResponse,
    LoginUser,
    OAuthGoogleAuthorizeResponse,
    OAuthGoogleCallbackResponse,
    OAuthLinkRequest,
    OAuthLoginRequest,
    OAuthProviderResponse,
    RefreshResponse,
)
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.services.alert_service import emit_security_alert
from app.services.token_service import (
    RefreshTokenReuseDetectedError,
    TokenValidationError,
    build_refresh_session_expiry,
    clear_auth_cookies,
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    build_fingerprint,
    parse_device_info,
    persist_refresh_jti,
    revoke_all_user_sessions_and_tokens,
    revoke_jti,
    rotate_refresh_token_or_revoke_all,
    set_auth_cookies,
    verify_mfa_token,
    verify_refresh_token,
)
from app.services.auth_service import (
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.services.email_service import EmailDeliveryError, send_email
from app.services.oauth_service import (
    OAuthFlowError,
    SUPPORTED_OAUTH_PROVIDERS,
    build_google_authorization_url,
    consume_oauth_state,
    exchange_google_code_for_tokens,
    fetch_google_userinfo,
    generate_oauth_state,
    maybe_encrypt_token,
    persist_oauth_state,
    validate_oauth_provider,
)
from app.services.risk_engine import assess_login_risk
from app.services.totp_service import verify_totp_code
from app.utils.encryption import decrypt_text, encrypt_text, is_encrypted_text

router = APIRouter(prefix="/auth", tags=["auth"])


async def _upsert_device_best_effort(
    *,
    db: AsyncSession,
    user_id: UUID,
    fingerprint: Optional[str],
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> None:
    if not fingerprint:
        return
    try:
        await UserDeviceRepository(db).upsert_from_login(
            user_id=user_id,
            fingerprint=fingerprint,
            user_agent=user_agent or "unknown",
            ip_address=ip_address or "unknown",
            trusted=True,
        )
    except Exception:
        return


async def _send_new_user_email_best_effort(
    *,
    email: str,
    username: str,
    source: str,
) -> None:
    try:
        await send_email(
            to_email=email,
            subject="[LogOnService] Welcome to LogOnService",
            body_text=(
                f"Hello {username},\n\n"
                "Your account has been created successfully.\n"
                f"Signup source: {source}\n"
                f"Email: {email}\n"
            ),
        )
    except EmailDeliveryError:
        # Registration/login should not fail when SMTP is unavailable.
        return


async def _issue_login_session(
    *,
    db: AsyncSession,
    response: Response,
    user: User,
    user_agent: str,
    ip_address: str,
    mfa_authenticated: bool = False,
) -> None:
    refresh_jti = str(uuid4())
    device_info = parse_device_info(user_agent)
    fingerprint = build_fingerprint(ip_address)
    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        mfa_authenticated=mfa_authenticated,
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        role=user.role,
        jti=refresh_jti,
        mfa_authenticated=mfa_authenticated,
    )
    await persist_refresh_jti(
        user_id=str(user.id),
        jti=refresh_jti,
        device_info=device_info,
        fingerprint=fingerprint,
    )
    await SessionRepository(db).create_session(
        user_id=user.id,
        jti=refresh_jti,
        session_expires_at=build_refresh_session_expiry(),
    )
    await _upsert_device_best_effort(
        db=db,
        user_id=user.id,
        fingerprint=fingerprint,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    set_auth_cookies(response, access_token, refresh_token)


async def _ensure_google_oauth_user(
    *,
    db: AsyncSession,
    profile: dict,
) -> User:
    email = (profile.get("email") or "").strip().lower()
    if email:
        existing = await UserRepository(db).get_by_email(email)
        if existing:
            return existing

    base_name = (profile.get("name") or email.split("@")[0] or "google_user").lower()
    safe_base = re.sub(r"[^a-z0-9_]", "_", base_name).strip("_")[:20] or "google_user"
    user_repo = UserRepository(db)

    for attempt in range(100):
        suffix = "" if attempt == 0 else f"_{attempt}"
        candidate = f"{safe_base}{suffix}"[:150]
        if not await user_repo.get_by_username(candidate):
            user = User(
                email=email or f"{candidate}@logonservices.local",
                username=candidate,
                role="user",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            await _send_new_user_email_best_effort(
                email=user.email,
                username=user.username,
                source="oauth_google",
            )
            return user

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create user")


@router.get("/health")
def auth_health() -> Dict[str, str]:
    return {"status": "ok", "module": "auth"}


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
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

    user_agent = request.headers.get("user-agent") or ""
    ip_address = request.client.host if request.client else ""
    fingerprint = build_fingerprint(ip_address)
    is_new_device = False
    if fingerprint:
        try:
            known_device = await UserDeviceRepository(db).get_by_user_and_fingerprint(
                user_id=user.id,
                fingerprint=fingerprint,
            )
            is_new_device = known_device is None
        except Exception:
            is_new_device = False

    risk = assess_login_risk(
        ip_address=ip_address,
        is_new_device=is_new_device,
        user_agent=user_agent,
        mfa_enabled=bool(user.mfa_enabled),
    )
    if risk.level in {"high", "medium"}:
        await AuditRepository(db).create_event(
            user_id=user.id,
            event_type="LOGIN_RISK_EVALUATED",
            ip_address=ip_address or None,
            user_agent=user_agent or None,
            metadata={
                "risk_level": risk.level,
                "risk_score": risk.score,
                "reasons": risk.reasons,
            },
        )

    if risk.level == "high":
        await emit_security_alert(
            db=db,
            alert_type="HIGH_RISK_LOGIN_ATTEMPT",
            severity="high",
            user_id=user.id,
            ip_address=ip_address or None,
            user_agent=user_agent or None,
            metadata={
                "risk_level": risk.level,
                "risk_score": risk.score,
                "reasons": risk.reasons,
            },
        )
        if not (user.mfa_enabled and user.totp_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="High-risk login blocked. Enable MFA to continue.",
            )

    if user.mfa_enabled and user.totp_secret:
        return LoginResponse(
            message="MFA required",
            mfa_required=True,
            mfa_token=create_mfa_token(user_id=str(user.id), role=user.role),
        )

    await _issue_login_session(
        db=db,
        response=response,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return LoginResponse(
        message="Login successful",
        mfa_required=False,
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            is_verified=user.is_verified,
        ),
    )


@router.post("/login/mfa", response_model=RefreshResponse)
async def login_mfa(
    payload: LoginMFARequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    try:
        mfa_payload = verify_mfa_token(payload.mfa_token)
        user_id = UUID(mfa_payload["sub"])
    except (TokenValidationError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token")

    user = await UserRepository(db).get_by_id_with_relationships(user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token")
    if not user.mfa_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA is not enabled")

    decrypted_totp_secret = decrypt_text(user.totp_secret)
    if not verify_totp_code(secret=decrypted_totp_secret, code=payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    if not is_encrypted_text(user.totp_secret):
        user.totp_secret = encrypt_text(decrypted_totp_secret)
        await db.commit()

    user_agent = request.headers.get("user-agent") or ""
    ip_address = request.client.host if request.client else ""
    await _issue_login_session(
        db=db,
        response=response,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
        mfa_authenticated=True,
    )
    return RefreshResponse(message="MFA login successful")


@router.get("/oauth/providers", response_model=OAuthProviderResponse)
def list_oauth_providers() -> OAuthProviderResponse:
    return OAuthProviderResponse(providers=sorted(SUPPORTED_OAUTH_PROVIDERS))


@router.get("/oauth/google/authorize", response_model=OAuthGoogleAuthorizeResponse)
async def google_oauth_authorize() -> OAuthGoogleAuthorizeResponse:
    state = generate_oauth_state()
    try:
        authorization_url = build_google_authorization_url(state=state)
    except OAuthFlowError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    await persist_oauth_state(state=state, provider="google")
    return OAuthGoogleAuthorizeResponse(authorization_url=authorization_url, state=state)


@router.get("/oauth/google/callback", response_model=OAuthGoogleCallbackResponse)
async def google_oauth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> OAuthGoogleCallbackResponse:
    state_ok = await consume_oauth_state(state=state, expected_provider="google")
    if not state_ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OAuth state")

    try:
        token_payload = await exchange_google_code_for_tokens(code=code)
        profile = await fetch_google_userinfo(access_token=token_payload["access_token"])
    except OAuthFlowError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    provider_user_id = str(profile["sub"])
    linked = await OAuthRepository(db).get_by_provider_subject(
        provider="google",
        provider_user_id=provider_user_id,
    )

    if linked is None:
        user = await _ensure_google_oauth_user(db=db, profile=profile)
        await OAuthRepository(db).upsert_link(
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            access_token_encrypted=maybe_encrypt_token(token_payload.get("access_token")),
            refresh_token_encrypted=maybe_encrypt_token(token_payload.get("refresh_token")),
        )
        await AuditRepository(db).create_event(
            user_id=user.id,
            event_type="OAUTH_ACCOUNT_LINKED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "provider": "google",
                "provider_user_id": provider_user_id,
                "flow": "authorization_code_callback",
            },
        )
    else:
        user = await UserRepository(db).get_by_id_with_relationships(linked.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth account not linked")
        await OAuthRepository(db).upsert_link(
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            access_token_encrypted=maybe_encrypt_token(token_payload.get("access_token")),
            refresh_token_encrypted=maybe_encrypt_token(token_payload.get("refresh_token")),
        )

    if user.deleted_at is not None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    user_agent = request.headers.get("user-agent") or ""
    ip_address = request.client.host if request.client else ""
    await _issue_login_session(
        db=db,
        response=response,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await AuditRepository(db).create_event(
        user_id=user.id,
        event_type="OAUTH_LOGIN_SUCCESS",
        ip_address=ip_address or None,
        user_agent=user_agent or None,
        metadata={"provider": "google", "flow": "authorization_code_callback"},
    )

    return OAuthGoogleCallbackResponse(
        message="Google OAuth login successful",
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            is_verified=user.is_verified,
        ),
    )


@router.post("/oauth/link", response_model=RefreshResponse)
async def link_oauth_account(
    payload: OAuthLinkRequest,
    request: Request,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    try:
        provider = validate_oauth_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    existing = await OAuthRepository(db).get_by_provider_subject(
        provider=provider,
        provider_user_id=payload.provider_user_id,
    )
    if existing and existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OAuth identity already linked to another user",
        )

    await OAuthRepository(db).upsert_link(
        user_id=current_user.id,
        provider=provider,
        provider_user_id=payload.provider_user_id,
        access_token_encrypted=maybe_encrypt_token(payload.access_token),
        refresh_token_encrypted=maybe_encrypt_token(payload.refresh_token),
    )
    await AuditRepository(db).create_event(
        user_id=current_user.id,
        event_type="OAUTH_ACCOUNT_LINKED",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={
            "provider": provider,
            "provider_user_id": payload.provider_user_id,
        },
    )
    return RefreshResponse(message="OAuth account linked")


@router.post("/oauth/login", response_model=LoginResponse)
async def oauth_login(
    payload: OAuthLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    try:
        provider = validate_oauth_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    oauth_account = await OAuthRepository(db).get_by_provider_subject(
        provider=provider,
        provider_user_id=payload.provider_user_id,
    )
    if oauth_account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OAuth account not linked",
        )

    user = await UserRepository(db).get_by_id_with_relationships(oauth_account.user_id)
    if user is None or user.deleted_at is not None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth account not linked")

    user_agent = request.headers.get("user-agent") or ""
    ip_address = request.client.host if request.client else ""
    await _issue_login_session(
        db=db,
        response=response,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await AuditRepository(db).create_event(
        user_id=user.id,
        event_type="OAUTH_LOGIN_SUCCESS",
        ip_address=ip_address or None,
        user_agent=user_agent or None,
        metadata={"provider": provider},
    )
    return LoginResponse(
        message="OAuth login successful",
        mfa_required=False,
        user=LoginUser(
            id=str(user.id),
            email=user.email,
            username=user.username,
            role=user.role,
            is_verified=user.is_verified,
        ),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_user(
            email=payload.email,
            username=payload.username,
            password=payload.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    await _send_new_user_email_best_effort(
        email=user.email,
        username=user.username,
        source="register",
    )

    return RegisterResponse(
        message="Registration successful",
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
    _: None = Depends(verify_csrf),
    refresh_token: str = Depends(get_refresh_token),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
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

    current_jti = payload["jti"]
    new_jti = str(uuid4())
    device_info = parse_device_info(request.headers.get("user-agent"))
    fingerprint = build_fingerprint(request.client.host if request.client else None)
    try:
        access_token, new_refresh_token = await rotate_refresh_token_or_revoke_all(
            db=db,
            user_id=str(user.id),
            current_jti=current_jti,
            new_jti=new_jti,
            role=user.role,
            mfa_authenticated=bool(payload.get("mfa_authenticated")),
            device_info=device_info,
            fingerprint=fingerprint,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except RefreshTokenReuseDetectedError:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions revoked.",
        )

    set_auth_cookies(response, access_token, new_refresh_token)
    return RefreshResponse(message="Token refresh successful")


@router.post("/logout", response_model=RefreshResponse)
async def logout(
    request: Request,
    response: Response,
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            payload = verify_refresh_token(refresh_token)
            await revoke_jti(user_id=payload["sub"], jti=payload["jti"])
            await SessionRepository(db).revoke_session_by_jti(payload["jti"])
        except TokenValidationError:
            pass

    clear_auth_cookies(response)
    return RefreshResponse(message="Logout successful")


@router.post("/logout-all", response_model=RefreshResponse)
async def logout_all_devices(
    response: Response,
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    await revoke_all_user_sessions_and_tokens(db=db, user_id=str(current_user.id))
    clear_auth_cookies(response)
    return RefreshResponse(message="All sessions revoked")
