from __future__ import annotations

import json
import secrets
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis_client
from app.utils.encryption import encrypt_text


SUPPORTED_OAUTH_PROVIDERS = {"google", "github"}


def normalize_oauth_provider(provider: str) -> str:
    return provider.strip().lower()


def validate_oauth_provider(provider: str) -> str:
    normalized = normalize_oauth_provider(provider)
    if normalized not in SUPPORTED_OAUTH_PROVIDERS:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    return normalized


def maybe_encrypt_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    return encrypt_text(token)


class OAuthFlowError(Exception):
    pass


def _oauth_state_key(state: str) -> str:
    return f"oauth:state:{state}"


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


async def persist_oauth_state(
    *,
    state: str,
    provider: str,
    redis_client: Optional[Redis] = None,
) -> None:
    redis_conn = redis_client or get_redis_client()
    payload = json.dumps({"provider": provider}, separators=(",", ":"))
    await redis_conn.set(_oauth_state_key(state), payload, ex=settings.OAUTH_STATE_TTL_SECONDS)


async def consume_oauth_state(
    *,
    state: str,
    expected_provider: str,
    redis_client: Optional[Redis] = None,
) -> bool:
    redis_conn = redis_client or get_redis_client()
    key = _oauth_state_key(state)
    payload = await redis_conn.get(key)
    if not payload:
        return False
    await redis_conn.delete(key)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return False
    return data.get("provider") == expected_provider


def build_google_authorization_url(*, state: str) -> str:
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_REDIRECT_URI:
        raise OAuthFlowError("Google OAuth is not configured")

    query = urlencode(
        {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": settings.GOOGLE_OAUTH_SCOPES,
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return f"{settings.GOOGLE_OAUTH_AUTH_URL}?{query}"


async def exchange_google_code_for_tokens(*, code: str) -> dict[str, Any]:
    if (
        not settings.GOOGLE_OAUTH_CLIENT_ID
        or not settings.GOOGLE_OAUTH_CLIENT_SECRET
        or not settings.GOOGLE_OAUTH_REDIRECT_URI
    ):
        raise OAuthFlowError("Google OAuth is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.GOOGLE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        raise OAuthFlowError("Google token exchange failed")

    payload = response.json()
    if "access_token" not in payload:
        raise OAuthFlowError("Google token exchange returned invalid payload")
    return payload


async def fetch_google_userinfo(*, access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            settings.GOOGLE_OAUTH_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise OAuthFlowError("Google userinfo request failed")

    payload = response.json()
    if not payload.get("sub"):
        raise OAuthFlowError("Google userinfo payload missing subject")
    return payload
