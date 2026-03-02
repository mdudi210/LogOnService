from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import uuid4

import jwt
from fastapi import Response
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE


class TokenValidationError(Exception):
    pass


def _build_token(
    *,
    user_id: str,
    role: str,
    token_type: str,
    expires_in_minutes: int,
    secret: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        "jti": str(uuid4()),
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


def create_refresh_token(user_id: str, role: str) -> str:
    return _build_token(
        user_id=user_id,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        secret=settings.JWT_REFRESH_SECRET_KEY,
    )


def _decode_token(token: str, secret: str, expected_type: str) -> Dict[str, str]:
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise TokenValidationError("Invalid token") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise TokenValidationError("Invalid token type")

    if not payload.get("sub") or not payload.get("role"):
        raise TokenValidationError("Token payload missing required claims")

    return payload


def verify_access_token(token: str) -> Dict[str, str]:
    return _decode_token(token, settings.JWT_SECRET_KEY, ACCESS_TOKEN_TYPE)


def verify_refresh_token(token: str) -> Dict[str, str]:
    return _decode_token(token, settings.JWT_REFRESH_SECRET_KEY, REFRESH_TOKEN_TYPE)


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
