from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_access_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@test.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def test_logout_all_revokes_sessions(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_revoke_all_user_sessions_and_tokens(**kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.revoke_all_user_sessions_and_tokens",
        fake_revoke_all_user_sessions_and_tokens,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.post("/auth/logout-all", headers={"X-CSRF-Token": "csrf-token"})

    assert response.status_code == 200
    assert response.json()["message"] == "All sessions revoked"


def test_logout_all_requires_csrf(monkeypatch) -> None:
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
        response = client.post("/auth/logout-all")

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"
