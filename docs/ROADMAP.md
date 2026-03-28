# Roadmap

## Completed
- Async backend migration and production-style connection pooling.
- JWT access/refresh/mfa token model with cookie transport.
- Redis-backed refresh token lifecycle and replay detection.
- Session management endpoints.
- CSRF protection and RBAC (admin MFA claim enforcement).
- MFA (TOTP) setup/verify and login step-up.
- Audit log persistence + admin observability endpoint.
- Optional SMTP security alerts + structured security-event logs.
- Frontend module with user/admin dashboards.
- Postman E2E single-run collection.
- CI test workflow.

## Next Milestones
1. Backend feature-governance APIs to replace frontend-local admin config placeholders.
2. CI quality gates:
   - lint (`ruff`)
   - type checks (`mypy`)
   - dependency/container scans.
3. Production hardening:
   - secrets rotation policies
   - environment profile lock-down
   - cookie/TLS policy validation by environment.
4. Security analytics:
   - event dashboards
   - alert thresholds and escalation.
5. Expanded security testing:
   - replay race conditions
   - cookie/csrf edge paths
   - abuse-rate testing.
