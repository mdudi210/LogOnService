from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import InvalidCredentialsError


client = TestClient(app)


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@test.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.mfa_enabled = False
        self.totp_secret = None


def test_login_success(monkeypatch) -> None:
    async def fake_login(self, email_or_username: str, password: str):
        return DummyUser()

    async def fake_persist_refresh_jti(**kwargs):
        return None

    async def fake_create_session(self, **kwargs):
        return None

    monkeypatch.setattr("app.services.auth_service.AuthService.login", fake_login)
    monkeypatch.setattr("app.api.routes.auth.persist_refresh_jti", fake_persist_refresh_jti)
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.create_session",
        fake_create_session,
    )

    response = client.post(
        "/auth/login",
        json={"email_or_username": "admin@test.local", "password": "Admin@12345"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert data["user"]["role"] == "admin"
    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in item for item in cookies)
    assert any("refresh_token=" in item for item in cookies)
    assert any("csrf_token=" in item for item in cookies)


def test_login_invalid_credentials(monkeypatch) -> None:
    async def fake_login(self, email_or_username: str, password: str):
        raise InvalidCredentialsError("Invalid credentials")

    monkeypatch.setattr("app.services.auth_service.AuthService.login", fake_login)

    response = client.post(
        "/auth/login",
        json={"email_or_username": "admin@test.local", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email/username or password"
