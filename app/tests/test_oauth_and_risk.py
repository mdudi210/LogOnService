from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.risk_engine import RiskAssessment
from app.services.token_service import create_access_token


class DummyUser:
    def __init__(self):
        self.id = uuid4()
        self.email = "user@logonservices.local"
        self.username = "user_test"
        self.role = "user"
        self.is_verified = True
        self.is_active = True
        self.deleted_at = None
        self.mfa_enabled = False
        self.totp_secret = None


class DummyAdminUser(DummyUser):
    def __init__(self):
        super().__init__()
        self.role = "admin"


def _set_csrf(client: TestClient, value: str = "csrf-token") -> dict[str, str]:
    client.cookies.set("csrf_token", value)
    return {"X-CSRF-Token": value}


def test_oauth_link_success(monkeypatch) -> None:
    user = DummyUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_get_by_provider_subject(self, provider: str, provider_user_id: str):
        return None

    async def fake_upsert_link(self, **kwargs):
        class Linked:
            user_id = user.id

        return Linked()

    async def fake_audit_event(self, **kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.oauth_repository.OAuthRepository.get_by_provider_subject",
        fake_get_by_provider_subject,
    )
    monkeypatch.setattr(
        "app.repositories.oauth_repository.OAuthRepository.upsert_link",
        fake_upsert_link,
    )
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.create_event",
        fake_audit_event,
    )

    access = create_access_token(user_id=str(user.id), role=user.role)
    with TestClient(app) as client:
        client.cookies.set("access_token", access)
        response = client.post(
            "/auth/oauth/link",
            headers=_set_csrf(client),
            json={
                "provider": "google",
                "provider_user_id": "google-user-123",
                "access_token": "provider-access",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "OAuth account linked"


def test_oauth_login_success(monkeypatch) -> None:
    user = DummyUser()

    class LinkedAccount:
        def __init__(self):
            self.user_id = user.id

    async def fake_get_by_provider_subject(self, provider: str, provider_user_id: str):
        return LinkedAccount()

    async def fake_get_by_id_with_relationships(self, user_id):
        return user

    async def fake_persist_refresh_jti(**kwargs):
        return None

    async def fake_create_session(self, **kwargs):
        return None

    async def fake_upsert_device(self, **kwargs):
        return None

    async def fake_audit_event(self, **kwargs):
        return None

    monkeypatch.setattr(
        "app.repositories.oauth_repository.OAuthRepository.get_by_provider_subject",
        fake_get_by_provider_subject,
    )
    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr("app.api.routes.auth.persist_refresh_jti", fake_persist_refresh_jti)
    monkeypatch.setattr(
        "app.repositories.session_repository.SessionRepository.create_session",
        fake_create_session,
    )
    monkeypatch.setattr(
        "app.repositories.user_device_repository.UserDeviceRepository.upsert_from_login",
        fake_upsert_device,
    )
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.create_event",
        fake_audit_event,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/oauth/login",
            json={"provider": "google", "provider_user_id": "google-user-123"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "OAuth login successful"
    cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in item for item in cookies)
    assert any("refresh_token=" in item for item in cookies)


def test_login_high_risk_without_mfa_blocked(monkeypatch) -> None:
    user = DummyUser()

    async def fake_login(self, email_or_username: str, password: str):
        return user

    async def fake_emit_security_alert(**kwargs):
        return None

    async def fake_audit_event(self, **kwargs):
        return None

    monkeypatch.setattr("app.services.auth_service.AuthService.login", fake_login)
    monkeypatch.setattr(
        "app.api.routes.auth.assess_login_risk",
        lambda **kwargs: RiskAssessment(level="high", score=90, reasons=["new_device"]),
    )
    monkeypatch.setattr("app.api.routes.auth.emit_security_alert", fake_emit_security_alert)
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.create_event",
        fake_audit_event,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email_or_username": "user@logonservices.local", "password": "User@12345"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "High-risk login blocked. Enable MFA to continue."


def test_admin_security_events_endpoint(monkeypatch) -> None:
    admin = DummyAdminUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return admin

    class Event:
        def __init__(self):
            self.id = uuid4()
            self.created_at = datetime.utcnow()
            self.user_id = admin.id
            self.ip_address = "127.0.0.1"
            self.user_agent = "pytest"
            self.event_metadata = {
                "alert_type": "REFRESH_TOKEN_REUSE_DETECTED",
                "severity": "critical",
                "note": "example",
            }

    async def fake_list_security_events(self, **kwargs):
        return [Event()]

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.list_security_events",
        fake_list_security_events,
    )

    token = create_access_token(
        user_id=str(admin.id),
        role=admin.role,
        mfa_authenticated=True,
    )
    with TestClient(app) as client:
        client.cookies.set("access_token", token)
        response = client.get("/users/admin/security-events")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["events"][0]["severity"] == "critical"


def test_admin_security_events_export_csv(monkeypatch) -> None:
    admin = DummyAdminUser()

    async def fake_get_by_id_with_relationships(self, user_id):
        return admin

    class Event:
        def __init__(self):
            self.id = uuid4()
            self.created_at = datetime.utcnow()
            self.user_id = admin.id
            self.ip_address = "127.0.0.1"
            self.user_agent = "pytest"
            self.event_metadata = {
                "alert_type": "HIGH_RISK_LOGIN_ATTEMPT",
                "severity": "high",
                "reason": "new_device",
            }

    async def fake_list_security_events(self, **kwargs):
        return [Event()]

    monkeypatch.setattr(
        "app.repositories.user_repository.UserRepository.get_by_id_with_relationships",
        fake_get_by_id_with_relationships,
    )
    monkeypatch.setattr(
        "app.repositories.audit_repository.AuditRepository.list_security_events",
        fake_list_security_events,
    )

    token = create_access_token(
        user_id=str(admin.id),
        role=admin.role,
        mfa_authenticated=True,
    )
    with TestClient(app) as client:
        client.cookies.set("access_token", token)
        response = client.get("/users/admin/security-events/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "HIGH_RISK_LOGIN_ATTEMPT" in response.text
