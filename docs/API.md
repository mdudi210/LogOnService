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
  "email_or_username": "admin@logonservices.local",
  "password": "Admin@12345"
}
```
Response body:
```json
{
  "message": "Login successful",
  "user": {
    "id": "...",
    "email": "admin@logonservices.local",
    "username": "admin_test",
    "role": "admin",
    "is_verified": true
  }
}
```
Cookies set:
- `access_token` (HttpOnly)
- `refresh_token` (HttpOnly)

### `POST /auth/register`
- Creates a new user account.
- Sends welcome email to the registered email address (best-effort).

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

### `GET /auth/oauth/github/authorize`
- Creates OAuth `state`, stores it in Redis, and returns GitHub authorization URL.

### `GET /auth/oauth/github/callback?code=...&state=...`
- Validates OAuth `state`, exchanges authorization `code` with GitHub, fetches user profile/email, links/creates user, and issues local auth cookies.

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

### `GET /users/me/sessions`
- Lists active sessions for current user.
- Requires `access_token` and `refresh_token` cookies.

### `DELETE /users/me/sessions/{jti}`
- Revokes a specific session owned by current user.
- Requires CSRF.

### `DELETE /users/me/sessions`
- Revokes all sessions except current one.
- Requires CSRF and `refresh_token` cookie.

### `GET /users/admin/health`
- Requires valid `access_token` cookie.
- Requires role `admin`.
- Returns `403 Insufficient permissions` for non-admin.

### `GET /users/admin/security-events`
- Admin-only JSON view of security alerts from audit logs.
- Query params: `limit`, `severity`, `alert_type`, `event_type`.

### `GET /users/admin/security-events/export`
- Admin-only CSV export for incident response workflows.
- Query params: `limit`, `severity`, `alert_type`.

### `GET /users/admin/activity`
- Admin-only activity log view (login/logout/session/security operations).
- Query params: `limit`, `event_type`, `user_id`.

### `POST /users/admin/security-events/test-alert`
- Admin-only endpoint to emit a low-severity manual test security alert.
- Requires auth + CSRF (`X-CSRF-Token`).
- Useful for validating email/webhook alert delivery with local Mailpit.
- Security alert emails are sent to configured recipients from `ALERT_EMAIL_TO` and `SECURITY_ALERT_EMAIL` (both support comma-separated values).

## MFA
### `GET /mfa/options`
- Returns available MFA methods and currently enabled methods for logged-in user.

### `POST /mfa/setup`
- Starts TOTP MFA setup (returns secret + provisioning URI).

### `POST /mfa/verify`
- Verifies TOTP code and enables TOTP MFA.

### `POST /mfa/setup/email`
- Sends Email MFA setup code to the logged-in user email.

### `POST /mfa/verify/email`
- Verifies Email MFA setup code and enables Email MFA.

### `POST /auth/login/mfa`
- Supports `method=totp` or `method=email` with MFA code.

## Auth Error Codes
- `401 Missing access token`
- `401 Invalid access token`
- `401 Missing refresh token`
- `401 Invalid refresh token`
- `401 Invalid email/username or password`
- `403 User account is inactive`
- `403 Insufficient permissions`
- `403 High-risk login blocked. Enable MFA to continue.`
