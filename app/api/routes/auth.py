from typing import Dict
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, verify_csrf
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import (
    LoginMFARequest,
    LoginRequest,
    LoginResponse,
    LoginUser,
    RefreshResponse,
)
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
from app.schemas.auth import RegisterRequest, RegisterResponse
from app.services.auth_service import (
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.repositories.user_repository import UserRepository
from app.services.totp_service import verify_totp_code

router = APIRouter(prefix="/auth", tags=["auth"])


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

    if user.mfa_enabled and user.totp_secret:
        return LoginResponse(
            message="MFA required",
            mfa_required=True,
            mfa_token=create_mfa_token(user_id=str(user.id), role=user.role),
        )

    refresh_jti = str(uuid4())
    device_info = parse_device_info(request.headers.get("user-agent"))
    fingerprint = build_fingerprint(request.client.host if request.client else None)
    access_token = create_access_token(user_id=str(user.id), role=user.role, mfa_authenticated=False)
    refresh_token = create_refresh_token(
        user_id=str(user.id), role=user.role, jti=refresh_jti, mfa_authenticated=False
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
    set_auth_cookies(response, access_token, refresh_token)

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
    if not verify_totp_code(secret=user.totp_secret, code=payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    refresh_jti = str(uuid4())
    device_info = parse_device_info(request.headers.get("user-agent"))
    fingerprint = build_fingerprint(request.client.host if request.client else None)
    access_token = create_access_token(user_id=str(user.id), role=user.role, mfa_authenticated=True)
    refresh_token = create_refresh_token(
        user_id=str(user.id), role=user.role, jti=refresh_jti, mfa_authenticated=True
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
    set_auth_cookies(response, access_token, refresh_token)
    return RefreshResponse(message="MFA login successful")


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
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

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
