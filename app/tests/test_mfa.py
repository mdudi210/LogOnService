from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_mfa_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@test.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None
        self.mfa_enabled = True
        self.totp_secret = "BASE32SECRET"


def test_login_returns_mfa_challenge_when_enabled(monkeypatch) -> None:
    user = DummyUser()

    async def fake_login(self, email_or_username: str, password: str):
        return user

    monkeypatch.setattr("app.services.auth_service.AuthService.login", fake_login)

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email_or_username": "admin@test.local", "password": "Admin@12345"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mfa_required"] is True
    assert payload["mfa_token"]
    assert payload["user"] is None
    cookies = response.headers.get_list("set-cookie")
    assert not any("access_token=" in item for item in cookies)
    assert not any("refresh_token=" in item for item in cookies)


def test_login_mfa_success_sets_auth_cookies(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_persist_refresh_jti(**kwargs):
        return None

    async def fake_create_session(self, **kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr("app.api.routes.auth.verify_totp_code", lambda **kwargs: True)
    monkeypatch.setattr("app.api.routes.auth.persist_refresh_jti", fake_persist_refresh_jti)
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.create_session",
        fake_create_session,
    )

    token = create_mfa_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        response = client.post(
            "/auth/login/mfa",
            json={"mfa_token": token, "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "MFA login successful"
    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in item for item in cookies)
    assert any("refresh_token=" in item for item in cookies)
