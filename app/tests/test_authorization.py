from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_access_token


class DummyUser:
    def __init__(self, role: str):
        self.id = uuid4()
        self.email = f"{role}@test.local"
        self.username = f"{role}_test"
        self.role = role
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def test_admin_route_allows_admin_role(monkeypatch) -> None:
    user = DummyUser(role="admin")

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role="admin")

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/admin/health")

    assert response.status_code == 200
    assert response.json()["scope"] == "admin"


def test_admin_route_forbidden_for_user_role(monkeypatch) -> None:
    user = DummyUser(role="user")

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role="user")

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/admin/health")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_admin_route_missing_access_cookie() -> None:
    with TestClient(app) as client:
        response = client.get("/users/admin/health")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing access token"


def test_admin_route_rejects_token_db_role_mismatch(monkeypatch) -> None:
    user = DummyUser(role="user")

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    access = create_access_token(user_id=str(user.id), role="admin")

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/admin/health")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access token"
