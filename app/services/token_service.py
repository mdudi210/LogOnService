from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import jwt
from fastapi import Response
from jwt import InvalidTokenError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.core.redis import get_redis_client
from app.repositories.session_repository import SessionRepository


class TokenValidationError(Exception):
    pass


class RefreshTokenReuseDetectedError(Exception):
    pass


def _refresh_jti_key(jti: str) -> str:
    return f"auth:refresh:jti:{jti}"


def _user_jti_set_key(user_id: str) -> str:
    return f"auth:user:jtis:{user_id}"


def _build_token(
    *,
    user_id: str,
    role: str,
    token_type: str,
    expires_in_minutes: int,
    secret: str,
    jti: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        "jti": jti or str(uuid4()),
    }
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_SECRET_KEY,
    )


def create_refresh_token(user_id: str, role: str, jti: Optional[str] = None) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_REFRESH_SECRET_KEY,
        jti=jti,
    )


def build_refresh_session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)


def _decode_token(token: str, secret: str, expected_type: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise TokenValidationError("Invalid token") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise TokenValidationError("Invalid token type")

    if not payload.get("sub") or not payload.get("role") or not payload.get("jti"):
        raise TokenValidationError("Token payload missing required claims")

    return payload


def verify_access_token(token: str) -> Dict[str, Any]:
    return _decode_token(token, settings.JWT_SECRET_KEY, ACCESS_TOKEN_TYPE)


def verify_refresh_token(token: str) -> Dict[str, Any]:
    return _decode_token(token, settings.JWT_REFRESH_SECRET_KEY, REFRESH_TOKEN_TYPE)


async def persist_refresh_jti(
    *,
    user_id: str,
    jti: str,
    ttl_seconds: Optional[int] = None,
    redis_client: Optional[Redis] = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    ttl = ttl_seconds or settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60

    await redis_conn.set(_refresh_jti_key(jti), user_id, ex=ttl)
    await redis_conn.sadd(_user_jti_set_key(user_id), jti)
    await redis_conn.expire(_user_jti_set_key(user_id), ttl)


async def consume_refresh_jti(
    *,
    user_id: str,
    jti: str,
    redis_client: Optional[Redis] = None,
) -> bool:
    redis_conn = redis_client or get_redis_client()
    key = _refresh_jti_key(jti)

    stored_user_id = await redis_conn.get(key)
    if not stored_user_id or stored_user_id != user_id:
        return False

    await redis_conn.delete(key)
    await redis_conn.srem(_user_jti_set_key(user_id), jti)
    return True


async def revoke_jti(
    *,
    user_id: str,
    jti: str,
    redis_client: Optional[Redis] = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    await redis_conn.delete(_refresh_jti_key(jti))
    await redis_conn.srem(_user_jti_set_key(user_id), jti)


async def revoke_all_user_sessions_and_tokens(
    *,
    db: AsyncSession,
    user_id: str,
    redis_client: Optional[Redis] = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    jtis = await SessionRepository(db).delete_all_user_sessions(UUID(user_id))

    if jtis:
        refresh_keys = [_refresh_jti_key(jti) for jti in jtis]
        await redis_conn.delete(*refresh_keys)

    await redis_conn.delete(_user_jti_set_key(user_id))


async def rotate_refresh_token_or_revoke_all(
    *,
    db: AsyncSession,
    user_id: str,
    current_jti: str,
    new_jti: str,
    role: str,
    redis_client: Optional[Redis] = None,
) -> tuple[str, str]:
    redis_conn = redis_client or get_redis_client()

    consumed = await consume_refresh_jti(user_id=user_id, jti=current_jti, redis_client=redis_conn)
    if not consumed:
        await revoke_all_user_sessions_and_tokens(db=db, user_id=user_id, redis_client=redis_conn)
        raise RefreshTokenReuseDetectedError("Refresh token reuse detected")

    await SessionRepository(db).revoke_session_by_jti(current_jti)

    access_token = create_access_token(user_id=user_id, role=role)
    refresh_token = create_refresh_token(user_id=user_id, role=role, jti=new_jti)

    await persist_refresh_jti(user_id=user_id, jti=new_jti, redis_client=redis_conn)
    await SessionRepository(db).create_session(
        user_id=UUID(user_id),
        jti=new_jti,
        session_expires_at=build_refresh_session_expiry(),
    )

    return access_token, refresh_token


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/")
