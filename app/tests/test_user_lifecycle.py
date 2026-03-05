from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import InvalidOldPasswordError
from app.services.token_service import create_access_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "newuser@test.local"
        self.username = "new_user"
        self.role = "user"
        self.is_verified = False
        self.is_active = True
        self.deleted_at = None


def test_register_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_register_user(self, **kwargs):
        return user

    monkeypatch.setattr("app.services.auth_service.AuthService.register_user", fake_register_user)

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "email": user.email,
                "username": user.username,
                "password": "StrongPass@123",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Registration successful"
    assert data["user"]["email"] == user.email
    assert data["user"]["role"] == "user"


def test_change_password_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_change_password(self, **kwargs):
        return None

    async def fake_revoke_all_user_sessions_and_tokens(**kwargs):
        return None

    async def fake_persist_refresh_jti(**kwargs):
        return None

    async def fake_create_session(self, **kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr("app.services.auth_service.AuthService.change_password", fake_change_password)
    monkeypatch.setattr(
        "app.api.routes.users.revoke_all_user_sessions_and_tokens",
        fake_revoke_all_user_sessions_and_tokens,
    )
    monkeypatch.setattr("app.api.routes.users.persist_refresh_jti", fake_persist_refresh_jti)
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.create_session",
        fake_create_session,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.post(
            "/users/me/change-password",
            headers={"X-CSRF-Token": "csrf-token"},
            json={"old_password": "OldPass@123", "new_password": "NewPass@123"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"
    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in item for item in cookies)
    assert any("refresh_token=" in item for item in cookies)
    assert any("csrf_token=" in item for item in cookies)


def test_change_password_wrong_old_password(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_change_password(self, **kwargs):
        raise InvalidOldPasswordError("Invalid old password")

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr("app.services.auth_service.AuthService.change_password", fake_change_password)

    access = create_access_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.post(
            "/users/me/change-password",
            headers={"X-CSRF-Token": "csrf-token"},
            json={"old_password": "WrongPass@123", "new_password": "NewPass@123"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Old password is incorrect"
