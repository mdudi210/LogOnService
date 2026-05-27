from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_access_token, create_refresh_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@logonservices.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def test_users_me_success(monkeypatch) -> None:
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
        response = client.get("/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
    assert data["role"] == "admin"


def test_users_me_missing_access_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


def test_users_me_invalid_access_token() -> None:
    with TestClient(app) as client:
        client.cookies.set("access_token", "not-a-valid-jwt")
        response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_users_me_rejects_refresh_token_in_access_cookie(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    refresh = create_refresh_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("access_token", refresh)
        response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_users_me_inactive_user(monkeypatch) -> None:
    user = DummyUser()
    user.is_active = False

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"


def test_users_me_role_mismatch_between_token_and_db(monkeypatch) -> None:
    user = DummyUser()
    user.role = "user"

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role="admin")

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"
