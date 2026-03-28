# Manual Testing Runbook

## Recommended Primary Method
Use Postman assets in `postman/`:
- `LogOnService.postman_collection.json`
- `LogOnService.local.postman_environment.json`
- `LogOnService.e2e_single_run.postman_collection.json`

Quick reference:
- [postman/README.md](/Users/manishdudi/Desktop/LogOnService/postman/README.md)

## Environment Preconditions
1. Backend running (`uvicorn app.main:app --reload` or Docker web service).
2. Postgres + Redis running.
3. Migrations applied (`alembic upgrade head`).

## Single-Run Validation
Import and run:
- `postman/LogOnService.e2e_single_run.postman_collection.json`
- request: `RUN E2E FLOW`

Flow steps:
1. Login
2. `/users/me`
3. `/users/me/sessions`
4. Refresh
5. Logout

## Full Manual Coverage Checklist
- Health endpoints return `200`.
- Login:
  - valid credentials => success
  - invalid credentials => `401`
- Protected route `/users/me`:
  - with auth cookie => `200`
  - without auth cookie => `401`
- CSRF-protected mutating routes:
  - missing/mismatch CSRF => `403`
- Session endpoints:
  - list sessions
  - revoke single non-current session
  - revoke all other sessions
- Admin endpoints:
  - non-admin denied
  - admin allowed (with MFA claim where required)
- MFA:
  - setup secret
  - verify code
  - login step-up (`/auth/login/mfa`)
- Audit/observability:
  - check `/users/admin/security-events` for emitted events

