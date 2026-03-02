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

## Authorization Guardrails
- `require_roles(...)` dependency validates endpoint-level role access.

## Required Production Hardening
- Replace default JWT keys with long random secrets managed by a secrets manager.
- Set `AUTH_COOKIE_SECURE=true` in HTTPS environments.
- Add CSRF defense strategy for cookie-based auth.
- Store refresh token state in Redis and implement reuse detection.
- Enable audit logging for all auth-sensitive actions.
