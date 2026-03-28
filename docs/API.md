# API Contract (Current)

Base URL: `http://127.0.0.1:8000`

## Health
- `GET /health`
- `GET /auth/health`
- `GET /users/health`

## Auth
### `POST /auth/login`
Request body:
```json
{
  "email_or_username": "admin@test.local",
  "password": "Admin@12345"
}
```
Response body:
```json
{
  "message": "Login successful",
  "user": {
    "id": "...",
    "email": "admin@test.local",
    "username": "admin_test",
    "role": "admin",
    "is_verified": true
  }
}
```
Cookies set:
- `access_token` (HttpOnly)
- `refresh_token` (HttpOnly)

### `POST /auth/refresh`
- Requires `refresh_token` cookie.
- Requires CSRF double-submit (`csrf_token` cookie + `X-CSRF-Token` header).
- Rotates `access_token` and `refresh_token` cookies.

### `POST /auth/logout`
- Clears `access_token` and `refresh_token` cookies.

### `GET /auth/oauth/providers`
- Returns supported OAuth providers (`google`, `github`).

### `GET /auth/oauth/google/authorize`
- Creates OAuth `state`, stores it in Redis, and returns Google authorization URL.

### `GET /auth/oauth/google/callback?code=...&state=...`
- Validates OAuth `state`, exchanges authorization `code` with Google, fetches user profile, links/creates user, and issues local auth cookies.

### `POST /auth/oauth/link`
- Requires valid `access_token` cookie.
- Requires CSRF double-submit.
- Links current user to external OAuth subject.

### `POST /auth/oauth/login`
- Logs in using a previously linked OAuth account.
- Sets `access_token` + `refresh_token` cookies on success.

## Users
### `GET /users/me`
- Requires valid `access_token` cookie.
- Returns authenticated user summary.

### `GET /users/admin/health`
- Requires valid `access_token` cookie.
- Requires role `admin`.
- Returns `403 Insufficient permissions` for non-admin.

### `GET /users/admin/security-events`
- Admin-only JSON view of security alerts from audit logs.
- Query params: `limit`, `severity`, `alert_type`.

### `GET /users/admin/security-events/export`
- Admin-only CSV export for incident response workflows.
- Query params: `limit`, `severity`, `alert_type`.

## Auth Error Codes
- `401 Missing access token`
- `401 Invalid access token`
- `401 Missing refresh token`
- `401 Invalid refresh token`
- `401 Invalid email/username or password`
- `403 User account is inactive`
- `403 Insufficient permissions`
- `403 High-risk login blocked. Enable MFA to continue.`
