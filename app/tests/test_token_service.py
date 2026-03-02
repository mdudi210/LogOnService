import pytest

from app.services.token_service import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)


def test_access_token_roundtrip() -> None:
    token = create_access_token(user_id="11111111-1111-1111-1111-111111111111", role="admin")
    payload = verify_access_token(token)
    assert payload["sub"] == "11111111-1111-1111-1111-111111111111"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(user_id="22222222-2222-2222-2222-222222222222", role="user")
    payload = verify_refresh_token(token)
    assert payload["sub"] == "22222222-2222-2222-2222-222222222222"
    assert payload["role"] == "user"
    assert payload["type"] == "refresh"


def test_access_verify_rejects_refresh_token() -> None:
    refresh = create_refresh_token(user_id="22222222-2222-2222-2222-222222222222", role="user")
    with pytest.raises(TokenValidationError):
        verify_access_token(refresh)


def test_refresh_verify_rejects_access_token() -> None:
    access = create_access_token(user_id="11111111-1111-1111-1111-111111111111", role="admin")
    with pytest.raises(TokenValidationError):
        verify_refresh_token(access)
