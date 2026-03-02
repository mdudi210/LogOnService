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
- Rotates `access_token` and `refresh_token` cookies.

### `POST /auth/logout`
- Clears `access_token` and `refresh_token` cookies.

## Users
### `GET /users/me`
- Requires valid `access_token` cookie.
- Returns authenticated user summary.

### `GET /users/admin/health`
- Requires valid `access_token` cookie.
- Requires role `admin`.
- Returns `403 Insufficient permissions` for non-admin.

## Auth Error Codes
- `401 Missing access token`
- `401 Invalid access token`
- `401 Missing refresh token`
- `401 Invalid refresh token`
- `401 Invalid email/username or password`
- `403 User account is inactive`
- `403 Insufficient permissions`
