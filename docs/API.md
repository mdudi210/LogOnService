# API Contract (Current)

Base URL: `http://localhost:8000` (or `http://127.0.0.1:8000`)

## Health
- `GET /health`
- `GET /auth/health`
- `GET /users/health`

## Authentication
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/login/mfa`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/logout-all`

## User
- `GET /users/me`
- `POST /users/me/change-password`
- `GET /users/me/sessions`
- `DELETE /users/me/sessions/{jti}`
- `DELETE /users/me/sessions` (revoke all other sessions)

## MFA
- `POST /mfa/setup`
- `POST /mfa/verify`

## Admin
- `GET /users/admin/health`
- `GET /users/admin/security-events`

## Cookie + CSRF Model
- Access and refresh tokens are issued as HttpOnly cookies.
- Mutating routes (`POST`, `PUT`, `PATCH`, `DELETE`) require:
  - `csrf_token` cookie
  - `X-CSRF-Token` header with matching value

## Session/Token Behavior
- Refresh token rotation is stateful (`jti` tracked in Redis).
- Replay/reuse detection revokes all sessions for compromised user.
- Session data is available through `/users/me/sessions` and admin observability endpoints.

## Primary Error Patterns
- `401 Missing access token`
- `401 Invalid access token`
- `401 Missing refresh token`
- `401 Invalid refresh token`
- `401 Refresh token reuse detected. All sessions revoked.`
- `403 CSRF validation failed`
- `403 Insufficient permissions`
- `403 MFA is required for admin access`
