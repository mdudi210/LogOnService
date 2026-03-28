# Security Model (Current)

## Password Storage
- Argon2id hashing (`argon2-cffi`).
- Explicit application-managed `password_salt` stored in DB.
- Verification flow uses `salt + plaintext` before hash verification.

## Token Security
- JWT access and refresh tokens with independent secrets.
- MFA token type supported for step-up login.
- Type claim enforcement (`access` vs `refresh`).
- Expiration enforced via `exp`.
- Tokens delivered via HttpOnly cookies only.

## Cookie Security
Configurable via env:
- `AUTH_COOKIE_SECURE`
- `AUTH_COOKIE_SAMESITE`
- `ACCESS_COOKIE_NAME`
- `REFRESH_COOKIE_NAME`
- `CSRF_COOKIE_NAME`
- `CSRF_HEADER_NAME`

## CSRF Protection
- Double-submit cookie pattern.
- Mutating requests require matching `csrf_token` cookie and `X-CSRF-Token` header.

## Authentication Guardrails
- DB user must exist.
- User must be active and not soft-deleted.
- Token role must match DB role to reduce stale privilege risk.

## Authorization Guardrails
- `require_roles(...)` dependency validates endpoint-level role access.
- Admin role paths also require `mfa_authenticated=true` in access token.

## Session Security
- Refresh token `jti` persisted in Redis with metadata.
- Rotation consumes old `jti` and issues a new one.
- Reuse detection triggers user-wide session/token revocation.
- Session lifecycle tracked in DB (`sessions` table) and Redis.

## Audit & Observability
- Security-relevant events persisted in `audit_logs`.
- Structured security event logs emitted via `app.security.events` logger.
- Optional SMTP alerts for selected event types:
  - `SECURITY_ALERTS_ENABLED`
  - `SECURITY_ALERT_EMAIL`
  - `SECURITY_ALERT_EVENT_TYPES`

## Sensitive Data Protection
- `totp_secret` encrypted at rest using application encryption utility.

## Remaining Production Hardening
- Replace default JWT keys with long random secrets managed by a secrets manager.
- Set `AUTH_COOKIE_SECURE=true` in HTTPS environments.
- Formalize key-rotation runbooks.
- Add security analytics dashboards and escalations.
