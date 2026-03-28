from __future__ import annotations

from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import SessionLocal
from app.repositories.audit_repository import AuditRepository


class AuditMiddleware(BaseHTTPMiddleware):
    """Best-effort audit trail for sensitive API operations."""

    _MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    _AUDIT_PATH_PREFIXES = ("/auth", "/users", "/mfa")
    _SKIP_PATH_PREFIXES = ("/docs", "/openapi.json", "/health")

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method not in self._MUTATING_METHODS:
            return response
        if any(request.url.path.startswith(prefix) for prefix in self._SKIP_PATH_PREFIXES):
            return response
        if not any(request.url.path.startswith(prefix) for prefix in self._AUDIT_PATH_PREFIXES):
            return response

        user_id = self._extract_subject_user_id(request.cookies.get("access_token"))
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Fail-open by design: auditing should never block auth availability.
        try:
            async with SessionLocal() as db:
                await AuditRepository(db).create_event(
                    user_id=user_id,
                    event_type="API_REQUEST",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                    },
                )
        except Exception:
            pass

        return response

    @staticmethod
    def _extract_subject_user_id(access_token: str | None) -> UUID | None:
        if not access_token:
            return None
        try:
            import jwt

            payload = jwt.decode(access_token, options={"verify_signature": False})
            subject = payload.get("sub")
            if not subject:
                return None
            return UUID(str(subject))
        except Exception:
            return None
