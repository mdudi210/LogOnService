from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_access_token, create_refresh_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "user@test.local"
        self.username = "user_test"
        self.role = "user"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


class DummySession:
    def __init__(self, user_id, jti: str):
        self.user_id = user_id
        self.jti = jti
        self.session_started_at = datetime.utcnow()
        self.session_expires_at = datetime.utcnow() + timedelta(hours=1)
        self.is_revoked = False


def test_list_my_sessions_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_get_active_sessions(self, user_id):
        return [DummySession(user.id, "jti-1"), DummySession(user.id, "jti-2")]

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.get_active_sessions",
        fake_get_active_sessions,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    refresh = create_refresh_token(user_id=str(user.id), role=user.role, jti="jti-1")
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("refresh_token", refresh)
        response = client.get("/users/me/sessions")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sessions"]) == 2
    assert payload["sessions"][0]["jti"] == "jti-1"
    assert payload["sessions"][0]["is_current"] is True
    assert payload["sessions"][1]["is_current"] is False


def test_revoke_my_session_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_get_by_jti(self, jti):
        return DummySession(user.id, jti)

    async def fake_revoke_jti(**kwargs):
        return None

    async def fake_revoke_session_by_jti(self, jti):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.get_by_jti",
        fake_get_by_jti,
    )
    monkeypatch.setattr("app.api.routes.users.revoke_jti", fake_revoke_jti)
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.revoke_session_by_jti",
        fake_revoke_session_by_jti,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.delete(
            "/users/me/sessions/jti-1",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Session revoked successfully"


def test_revoke_my_session_not_found_for_other_user(monkeypatch) -> None:
    user = DummyUser()
    other_user_id = uuid4()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_get_by_jti(self, jti):
        return DummySession(other_user_id, jti)

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.get_by_jti",
        fake_get_by_jti,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.delete(
            "/users/me/sessions/jti-1",
            headers={"X-CSRF-Token": "csrf-token"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_revoke_my_session_requires_csrf(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.delete("/users/me/sessions/jti-1")

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"


def test_revoke_other_sessions_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_revoke_other_sessions(self, user_id, exclude_jti):
        assert str(user_id) == str(user.id)
        assert exclude_jti == "current-jti"
        return ["old-jti-1", "old-jti-2"]

    async def fake_revoke_jti(**kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.revoke_other_sessions",
        fake_revoke_other_sessions,
    )
    monkeypatch.setattr("app.api.routes.users.revoke_jti", fake_revoke_jti)

    access = create_access_token(user_id=str(user.id), role=user.role)
    refresh = create_refresh_token(user_id=str(user.id), role=user.role, jti="current-jti")
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("refresh_token", refresh)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.delete("/users/me/sessions", headers={"X-CSRF-Token": "csrf-token"})

    assert response.status_code == 200
    assert response.json()["message"] == "Other sessions revoked successfully"


def test_list_my_sessions_requires_refresh_cookie(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/me/sessions")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing refresh token"
