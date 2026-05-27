from __future__ import annotations

import hashlib
import secrets
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.redis import get_redis_client
from app.services.email_service import EmailDeliveryError, send_email


def _setup_key(user_id: UUID) -> str:
    return f"mfa:email:setup:{user_id}"


def _login_key(user_id: UUID) -> str:
    return f"mfa:email:login:{user_id}"


def _code_ttl_seconds() -> int:
    return max(int(settings.MFA_TOKEN_EXPIRE_MINUTES) * 60, 60)


def _hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{code}".encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


async def _store_code(*, key: str, code: str) -> None:
    redis = get_redis_client()
    await redis.set(key, _hash_code(code), ex=_code_ttl_seconds())


async def _verify_code(*, key: str, code: str) -> bool:
    redis = get_redis_client()
    stored_hash = await redis.get(key)
    if not stored_hash:
        return False
    if stored_hash != _hash_code(code):
        return False
    await redis.delete(key)
    return True


async def send_email_mfa_setup_code(*, user_id: UUID, to_email: str) -> int:
    code = _generate_code()
    await _store_code(key=_setup_key(user_id), code=code)
    await send_email(
        to_email=to_email,
        subject="[LogOnService] Email MFA setup code",
        body_text=(
            "Use this code to enable Email MFA:\n\n"
            f"{code}\n\n"
            f"This code expires in {_code_ttl_seconds()} seconds."
        ),
    )
    return _code_ttl_seconds()


async def verify_email_mfa_setup_code(*, user_id: UUID, code: str) -> bool:
    return await _verify_code(key=_setup_key(user_id), code=code)


async def send_email_mfa_login_code(*, user_id: UUID, to_email: str) -> int:
    code = _generate_code()
    await _store_code(key=_login_key(user_id), code=code)
    await send_email(
        to_email=to_email,
        subject="[LogOnService] Email MFA login code",
        body_text=(
            "Use this code to finish signing in:\n\n"
            f"{code}\n\n"
            f"This code expires in {_code_ttl_seconds()} seconds."
        ),
    )
    return _code_ttl_seconds()


async def verify_email_mfa_login_code(*, user_id: UUID, code: str) -> bool:
    return await _verify_code(key=_login_key(user_id), code=code)


async def try_send_email_mfa_login_code(*, user_id: UUID, to_email: str) -> bool:
    try:
        await send_email_mfa_login_code(user_id=user_id, to_email=to_email)
        return True
    except EmailDeliveryError:
        return False

