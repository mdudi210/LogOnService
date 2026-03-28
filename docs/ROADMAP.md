# Roadmap

## Completed
- Async SQLAlchemy migration.
- JWT access/refresh token creation + verification.
- HttpOnly cookie-based auth transport.
- Salted Argon2 password verification.
- Auth and RBAC dependencies.
- Core auth boundary test coverage.
- Refresh token persistence in Redis with rotation tracking and reuse detection.
- Session table integration with token/session IDs.
- MFA implementation (TOTP flow).
- Audit middleware integration.
- Rate limiting middleware with Redis.
- CI workflow (tests + migration smoke checks).
- TOTP secret encryption at rest.
- OAuth provider integration with Google authorization-code callback.
- Security alerting pipeline + admin observability APIs (JSON/CSV exports).
- CI hardening with lint/type/security scans.
- Postman runner smoke suites for one-click verification.

## Next Milestones
1. Add GitHub/enterprise IdP OAuth callback flows.
2. Build SIEM/on-call escalation workflows and runbooks from webhook alerts.
3. Tighten CI quality gates (turn mypy/bandit/audit into required checks).
4. Session/device management APIs (list/revoke specific sessions/devices).
