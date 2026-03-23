from datetime import datetime
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


class DummyAuditEvent:
    def __init__(self, *, event_type: str):
        self.id = uuid4()
        self.user_id = uuid4()
        self.event_type = event_type
        self.ip_address = "127.0.0.1"
        self.user_agent = "pytest-agent"
        self.event_metadata = {"k": "v"}
        self.created_at = datetime.utcnow()


def test_admin_security_events_success(monkeypatch) -> None:
    admin = DummyUser(role="admin")

    async def fake_get_by_id_with_relationships(self, user_id):
        return admin

    async def fake_list_recent_events(self, limit=50, event_types=None):
        assert limit == 10
        assert event_types == ["TOKEN_REUSE_DETECTED"]
        return [DummyAuditEvent(event_type="TOKEN_REUSE_DETECTED")]

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.list_recent_events",
        fake_list_recent_events,
    )

    access = create_access_token(user_id=str(admin.id), role="admin", mfa_authenticated=True)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.get("/users/admin/security-events?limit=10&event_type=TOKEN_REUSE_DETECTED")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_type"] == "TOKEN_REUSE_DETECTED"


def test_admin_security_events_forbidden_for_non_admin(monkeypatch) -> None:
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
        response = client.get("/users/admin/security-events")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

