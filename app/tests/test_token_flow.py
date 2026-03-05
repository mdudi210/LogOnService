from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.token_service import (
    RefreshTokenReuseDetectedError,
    create_access_token,
    create_refresh_token,
)


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "admin@test.local"
        self.username = "admin_test"
        self.role = "admin"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None


def _set_csrf(client: TestClient, value: str = "csrf-token") -> dict[str, str]:
    client.cookies.set("csrf_token", value)
    return {"X-CSRF-Token": value}


def test_refresh_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )

    async def fake_rotate_refresh_token_or_revoke_all(**kwargs):
        return (
            create_access_token(user_id=str(user.id), role=user.role),
            create_refresh_token(user_id=str(user.id), role=user.role),
        )

    monkeypatch.setattr(
        "app.api.routes.auth.rotate_refresh_token_or_revoke_all",
        fake_rotate_refresh_token_or_revoke_all,
    )

    refresh = create_refresh_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("refresh_token", refresh)
        response = client.post("/auth/refresh", headers=_set_csrf(client))

        assert response.status_code == 200
        assert response.json()["message"] == "Token refresh successful"
        cookies = response.headers.get_list("set-cookie")
        assert any("access_token=" in item for item in cookies)
        assert any("refresh_token=" in item for item in cookies)


def test_refresh_missing_cookie() -> None:
    with TestClient(app) as client:
        response = client.post("/auth/refresh", headers=_set_csrf(client))
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing refresh token"


def test_refresh_missing_csrf_header() -> None:
    user = DummyUser()
    refresh = create_refresh_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("refresh_token", refresh)
        client.cookies.set("csrf_token", "csrf-token")
        response = client.post("/auth/refresh")

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"


def test_refresh_reuse_detection(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_rotate_refresh_token_or_revoke_all(**kwargs):
        raise RefreshTokenReuseDetectedError("Refresh token reuse detected")

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.api.routes.auth.rotate_refresh_token_or_revoke_all",
        fake_rotate_refresh_token_or_revoke_all,
    )

    refresh = create_refresh_token(user_id=str(user.id), role=user.role)

    with TestClient(app) as client:
        client.cookies.set("refresh_token", refresh)
        response = client.post("/auth/refresh", headers=_set_csrf(client))

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token reuse detected. All sessions revoked."
