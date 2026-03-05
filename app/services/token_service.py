from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import jwt
from fastapi import Response
from jwt import InvalidTokenError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import ACCESS_TOKEN_TYPE, MFA_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.core.redis import get_redis_client
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import SessionRepository


class TokenValidationError(Exception):
    pass


class RefreshTokenReuseDetectedError(Exception):
    pass


def _refresh_jti_key(jti: str) -> str:
    return f"auth:refresh:jti:{jti}"


def _user_jti_set_key(user_id: str) -> str:
    return f"auth:user:jtis:{user_id}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_unix_timestamp(value: datetime) -> int:
    return int(value.timestamp())


def _from_unix_timestamp(value: str) -> datetime:
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def parse_device_info(user_agent: Optional[str]) -> Dict[str, str]:
    """Parse minimal device metadata from User-Agent without paid/external services."""
    raw = (user_agent or "").strip()
    if not raw:
        return {"raw": "", "client": "unknown", "platform": "unknown"}

    client = raw.split(" ")[0] if " " in raw else raw
    platform = "unknown"
    if "(" in raw and ")" in raw:
        platform = raw[raw.find("(") + 1 : raw.find(")")]

    return {"raw": raw, "client": client[:120], "platform": platform[:200]}


def build_fingerprint(client_ip: Optional[str]) -> Optional[str]:
    if not client_ip:
        return None
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()


def _serialize_metadata(
    *,
    user_id: str,
    device_info: Dict[str, str],
    issued_at: datetime,
    expires_at: datetime,
    fingerprint: Optional[str] = None,
) -> Dict[str, str]:
    return {
        "user_id": user_id,
        "device_info": json.dumps(device_info, separators=(",", ":")),
        "issued_at": str(_to_unix_timestamp(issued_at)),
        "expires_at": str(_to_unix_timestamp(expires_at)),
        "fingerprint": fingerprint or "",
    }


def _deserialize_metadata(payload: Dict[str, str]) -> Dict[str, Any]:
    return {
        "user_id": payload["user_id"],
        "device_info": json.loads(payload.get("device_info", "{}")),
        "issued_at": _from_unix_timestamp(payload["issued_at"]),
        "expires_at": _from_unix_timestamp(payload["expires_at"]),
        "fingerprint": payload.get("fingerprint") or None,
    }


def _build_token(
    *,
    user_id: str,
    role: str,
    token_type: str,
    expires_in_minutes: int,
    secret: str,
    jti: Optional[str] = None,
    mfa_authenticated: bool = False,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        "jti": jti or str(uuid4()),
        "mfa_authenticated": mfa_authenticated,
    }
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, mfa_authenticated: bool = False) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_SECRET_KEY,
        mfa_authenticated=mfa_authenticated,
    )


def create_refresh_token(
    user_id: str,
    role: str,
    jti: Optional[str] = None,
    mfa_authenticated: bool = False,
) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_REFRESH_SECRET_KEY,
        jti=jti,
        mfa_authenticated=mfa_authenticated,
    )


def create_mfa_token(user_id: str, role: str) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=MFA_TOKEN_TYPE,
        expires_in_minutes=settings.MFA_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_SECRET_KEY,
        mfa_authenticated=False,
    )


def build_refresh_session_expiry() -> datetime:
    return _now_utc() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)


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


def verify_mfa_token(token: str) -> Dict[str, Any]:
    return _decode_token(token, settings.JWT_SECRET_KEY, MFA_TOKEN_TYPE)


async def persist_refresh_jti(
    *,
    user_id: str,
    jti: str,
    device_info: Optional[Dict[str, str]] = None,
    issued_at: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
    fingerprint: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    redis_client: Optional[Redis] = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    now = issued_at or _now_utc()
    expires = expires_at or (now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    ttl = ttl_seconds or max(int((expires - now).total_seconds()), 1)
    metadata = _serialize_metadata(
        user_id=user_id,
        device_info=device_info or parse_device_info(None),
        issued_at=now,
        expires_at=expires,
        fingerprint=fingerprint,
    )

    key = _refresh_jti_key(jti)
    await redis_conn.hset(key, mapping=metadata)
    await redis_conn.expire(key, ttl)
    await redis_conn.sadd(_user_jti_set_key(user_id), jti)
    await redis_conn.expire(_user_jti_set_key(user_id), ttl)


async def get_refresh_session_metadata(
    *, jti: str, redis_client: Optional[Redis] = None
) -> Optional[Dict[str, Any]]:
    redis_conn = redis_client or get_redis_client()
    payload = await redis_conn.hgetall(_refresh_jti_key(jti))
    if not payload:
        return None
    return _deserialize_metadata(payload)


async def get_all_user_refresh_session_metadata(
    *,
    user_id: str,
    redis_client: Optional[Redis] = None,
) -> list[dict[str, Any]]:
    redis_conn = redis_client or get_redis_client()
    jtis = await redis_conn.smembers(_user_jti_set_key(user_id))
    if not jtis:
        return []

    sessions: list[dict[str, Any]] = []
    for jti in jtis:
        metadata = await get_refresh_session_metadata(jti=jti, redis_client=redis_conn)
        if metadata is None:
            continue
        sessions.append({"jti": jti, **metadata})

    sessions.sort(key=lambda item: item["issued_at"])
    return sessions


async def consume_refresh_jti(
    *,
    user_id: str,
    jti: str,
    redis_client: Optional[Redis] = None,
) -> Optional[Dict[str, Any]]:
    redis_conn = redis_client or get_redis_client()
    key = _refresh_jti_key(jti)

    payload = await redis_conn.hgetall(key)
    if not payload:
        return None

    metadata = _deserialize_metadata(payload)
    if metadata["user_id"] != user_id:
        return None

    await redis_conn.delete(key)
    await redis_conn.srem(_user_jti_set_key(user_id), jti)
    return metadata


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
    mfa_authenticated: bool = False,
    device_info: Optional[Dict[str, str]] = None,
    fingerprint: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    redis_client: Optional[Redis] = None,
) -> tuple[str, str]:
    redis_conn = redis_client or get_redis_client()

    consumed_metadata = await consume_refresh_jti(
        user_id=user_id, jti=current_jti, redis_client=redis_conn
    )
    if not consumed_metadata:
        active_sessions = await get_all_user_refresh_session_metadata(
            user_id=user_id, redis_client=redis_conn
        )
        await AuditRepository(db).create_event(
            user_id=UUID(user_id),
            event_type="TOKEN_REUSE_DETECTED",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "triggering_jti": current_jti,
                "provided_device_info": device_info,
                "provided_fingerprint": fingerprint,
                "active_refresh_sessions": [
                    {
                        "jti": session["jti"],
                        "user_id": session["user_id"],
                        "device_info": session["device_info"],
                        "issued_at": session["issued_at"].isoformat(),
                        "expires_at": session["expires_at"].isoformat(),
                        "fingerprint": session["fingerprint"],
                    }
                    for session in active_sessions
                ],
            },
        )
        await revoke_all_user_sessions_and_tokens(db=db, user_id=user_id, redis_client=redis_conn)
        raise RefreshTokenReuseDetectedError("Refresh token reuse detected")

    await SessionRepository(db).revoke_session_by_jti(current_jti)

    access_token = create_access_token(
        user_id=user_id, role=role, mfa_authenticated=mfa_authenticated
    )
    refresh_token = create_refresh_token(
        user_id=user_id, role=role, jti=new_jti, mfa_authenticated=mfa_authenticated
    )

    now = _now_utc()
    expires = now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    await persist_refresh_jti(
        user_id=user_id,
        jti=new_jti,
        device_info=device_info or consumed_metadata["device_info"],
        issued_at=now,
        expires_at=expires,
        fingerprint=fingerprint if fingerprint is not None else consumed_metadata.get("fingerprint"),
        redis_client=redis_conn,
    )
    await SessionRepository(db).create_session(
        user_id=UUID(user_id),
        jti=new_jti,
        session_expires_at=expires,
    )

    return access_token, refresh_token


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)

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
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
