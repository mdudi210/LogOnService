from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import create_refresh_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@test.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def test_refresh_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    refresh = create_refresh_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("refresh_token", refresh)
        response = client.post("/auth/refresh")

        assert response.status_code == 200
        assert response.json()["message"] == "Token refresh successful"
        cookies = response.headers.get_list("set-cookie")
        assert any("access_token=" in item for item in cookies)
        assert any("refresh_token=" in item for item in cookies)


def test_refresh_missing_cookie() -> None:
    with TestClient(app) as client:
        response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing refresh token"
