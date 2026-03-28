# Security Model (Current)

## Password Storage
- Argon2id hashing (`argon2-cffi`).
- Explicit application-managed `password_salt` stored in DB.
- Verification flow uses `salt + plaintext` before hash verification.

## Token Security
- JWT access and refresh tokens with independent secrets.
- Type claim enforcement (`access` vs `refresh`).
- Expiration enforced via `exp`.
- Tokens delivered via HttpOnly cookies only.

## Cookie Security
Configurable via env:
- `AUTH_COOKIE_SECURE`
- `AUTH_COOKIE_SAMESITE`
- `ACCESS_COOKIE_NAME`
- `REFRESH_COOKIE_NAME`

## Authentication Guardrails
- DB user must exist.
- User must be active and not soft-deleted.
- Token role must match DB role to reduce stale privilege risk.
- Adaptive risk scoring on login (device novelty + network + user-agent heuristics).
- High-risk login attempts are blocked for users without MFA enabled.

## Authorization Guardrails
- `require_roles(...)` dependency validates endpoint-level role access.
- Admin routes enforce MFA-authenticated access token claims.
- Security event observability endpoint: `GET /users/admin/security-events`.

## Alerting Pipeline
- Security alerts are stored as `SECURITY_ALERT` records in `audit_logs`.
- Optional email notifications via `ALERT_EMAIL_TO`.
- Optional webhook notifications via `ALERT_WEBHOOK_URL`.
- Webhook templates support Slack and Discord payloads (`ALERT_WEBHOOK_FORMAT=auto|slack|discord`).
- Alert severity threshold controlled by `ALERT_MIN_SEVERITY` (`low|medium|high|critical`).

## Required Production Hardening
- Replace default JWT keys with long random secrets managed by a secrets manager.
- Set `AUTH_COOKIE_SECURE=true` in HTTPS environments.
- Configure CSRF header handling in frontend clients.
- Set dedicated `TOTP_ENCRYPTION_KEY` (not shared with JWT keys).
- Route alert webhooks to SIEM/on-call tooling.
