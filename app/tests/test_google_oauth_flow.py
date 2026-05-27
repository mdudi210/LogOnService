from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "google.user@logonservices.local"
        self.username = "google_user"
        self.role = "user"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def test_google_oauth_authorize_success(monkeypatch) -> None:
    async def fake_persist_oauth_state(**kwargs):
        return None

    monkeypatch.setattr("app.api.routes.auth.generate_oauth_state", lambda: "state-123")
    monkeypatch.setattr(
        "app.api.routes.auth.build_google_authorization_url",
        lambda **kwargs: "https://accounts.google.com/o/oauth2/v2/auth?state=state-123",
    )
    monkeypatch.setattr("app.api.routes.auth.persist_oauth_state", fake_persist_oauth_state)

    with TestClient(app) as client:
        response = client.get("/auth/oauth/google/authorize")

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "state-123"
    assert "accounts.google.com" in data["authorization_url"]


def test_google_oauth_callback_invalid_state(monkeypatch) -> None:
    async def fake_consume_state(**kwargs):
        return False

    monkeypatch.setattr("app.api.routes.auth.consume_oauth_state", fake_consume_state)

    with TestClient(app) as client:
        response = client.get("/auth/oauth/google/callback?code=abc&state=bad")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid OAuth state"


def test_google_oauth_callback_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_consume_state(**kwargs):
        return True

    async def fake_exchange_google_code_for_tokens(**kwargs):
        return {"access_token": "google-access-token", "refresh_token": "google-refresh-token"}

    async def fake_fetch_google_userinfo(**kwargs):
        return {"sub": "google-sub-123", "email": user.email, "name": "Google User"}

    async def fake_get_by_provider_subject(self, **kwargs):
        return None

    async def fake_ensure_google_oauth_user(**kwargs):
        return user

    async def fake_upsert_link(self, **kwargs):
        class Linked:
            user_id = user.id

        return Linked()

    async def fake_issue_login_session(**kwargs):
        return None

    async def fake_audit_event(self, **kwargs):
        return None

    monkeypatch.setattr("app.api.routes.auth.consume_oauth_state", fake_consume_state)
    monkeypatch.setattr(
        "app.api.routes.auth.exchange_google_code_for_tokens",
        fake_exchange_google_code_for_tokens,
    )
    monkeypatch.setattr("app.api.routes.auth.fetch_google_userinfo", fake_fetch_google_userinfo)
    monkeypatch.setattr(
        "app.repositories.oauth_repository.OAuthRepository.get_by_provider_subject",
        fake_get_by_provider_subject,
    )
    monkeypatch.setattr("app.api.routes.auth._ensure_google_oauth_user", fake_ensure_google_oauth_user)
    monkeypatch.setattr("app.repositories.oauth_repository.OAuthRepository.upsert_link", fake_upsert_link)
    monkeypatch.setattr("app.api.routes.auth._issue_login_session", fake_issue_login_session)
    monkeypatch.setattr("app.repositories.audit_repository.AuditRepository.create_event", fake_audit_event)

    with TestClient(app) as client:
        response = client.get("/auth/oauth/google/callback?code=abc123&state=state-123")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Google OAuth login successful"
    assert data["user"]["email"] == user.email
