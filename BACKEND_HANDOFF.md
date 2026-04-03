# LogOnService Backend Handoff

This document is the single backend handoff file for any frontend team or Codex session in another repository.

## 1) What This Backend Provides

- Cookie-based authentication API using FastAPI.
- JWT access + refresh tokens (stored in HttpOnly cookies).
- CSRF protection (double-submit cookie pattern).
- MFA (TOTP) setup and verification.
- Google OAuth authorization-code callback flow.
- Admin-only security events APIs (JSON + CSV export).
- Risk-aware login behavior and security alert hooks.

Base URL (local): `http://127.0.0.1:8000`
Swagger docs: `http://127.0.0.1:8000/docs`

## 2) Runtime + Setup

### Stack

- FastAPI + Starlette
- SQLAlchemy (async)
- Alembic migrations
- PostgreSQL
- Redis

### Local run

```bash
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

## 3) Required Environment Variables

Minimum required for startup:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `JWT_REFRESH_SECRET_KEY`
- `ALLOWED_CORS_ORIGINS`

Recommended security/feature vars:

- `TOTP_ENCRYPTION_KEY`
- `AUTH_COOKIE_SECURE`
- `AUTH_COOKIE_SAMESITE`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `ALERT_WEBHOOK_URL`
- `ALERT_WEBHOOK_FORMAT`
- `ALERT_MIN_SEVERITY`

## 4) Auth Model (Important for Frontend)

### Cookies used by backend

- `access_token` (HttpOnly)
- `refresh_token` (HttpOnly)
- `csrf_token` (readable cookie, used by frontend)

### How requests must be sent

- Always send credentials/cookies.
- For `POST`, `PUT`, `PATCH`, `DELETE`, include header:
  - `X-CSRF-Token: <csrf_token_cookie_value>`

Frontend clients must use:

- `fetch`: `credentials: "include"`
- Axios: `withCredentials: true`

If CSRF header is missing or mismatched, backend returns:

- `403 {"detail":"CSRF validation failed"}`

## 5) Endpoint Catalog

## System

- `GET /health`

## Auth (`/auth`)

- `GET /auth/health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/login/mfa`
- `POST /auth/refresh` (requires `refresh_token` cookie + CSRF header)
- `POST /auth/logout` (requires CSRF header)
- `POST /auth/logout-all` (requires auth + CSRF header)

### OAuth

- `GET /auth/oauth/providers`
- `GET /auth/oauth/google/authorize`
- `GET /auth/oauth/google/callback?code=...&state=...`
- `GET /auth/oauth/github/authorize`
- `GET /auth/oauth/github/callback?code=...&state=...`
- `POST /auth/oauth/link` (requires auth + CSRF)
- `POST /auth/oauth/login`

## MFA (`/mfa`)

- `GET /mfa/options` (available + enabled methods)
- `POST /mfa/setup` (requires auth + CSRF)
- `POST /mfa/verify` (requires auth + CSRF)
- `POST /mfa/setup/email` (requires auth + CSRF)
- `POST /mfa/verify/email` (requires auth + CSRF)

## Users (`/users`)

- `GET /users/health`
- `GET /users/me` (requires auth)
- `POST /users/me/change-password` (requires auth + CSRF)

### Admin

- `GET /users/admin/health` (admin + MFA-authenticated token)
- `GET /users/admin/security-events`
- `GET /users/admin/security-events/export` (CSV)
- `POST /users/admin/security-events/test-alert` (admin + CSRF, emits test alert for email/webhook verification)

## 6) Frontend Flow (Reference)

### Email/password login flow

1. Call `POST /auth/login`.
2. If `mfa_required=false`, user is logged in and cookies are set.
3. If `mfa_required=true`, call `POST /auth/login/mfa` with returned `mfa_token` + TOTP code.
4. Store no JWT in localStorage; backend uses HttpOnly cookies.

### Session refresh flow

1. On `401`, call `POST /auth/refresh`.
2. Send `X-CSRF-Token` from `csrf_token` cookie.
3. Retry original request after successful refresh.

### Logout flow

- Call `POST /auth/logout` with CSRF header.
- Backend clears auth cookies.

## 7) Google OAuth (Authorization Code)

Recommended frontend sequence:

1. Call `GET /auth/oauth/google/authorize`.
2. Redirect browser to returned `authorization_url`.
3. Google redirects to backend callback (`/auth/oauth/google/callback`).
4. Backend links/creates user, sets local auth cookies, returns user payload.

## 8) Error Semantics to Handle in Frontend

- `401 Missing access token`
- `401 Invalid access token`
- `401 Missing refresh token`
- `401 Invalid refresh token`
- `401 Refresh token reuse detected. All sessions revoked.`
- `403 CSRF validation failed`
- `403 MFA is required for admin access`
- `403 High-risk login blocked. Enable MFA to continue.`
- `409 OAuth identity already linked to another user`

## 9) CORS + Cookie Notes

- Backend allows credentials in CORS.
- `ALLOWED_CORS_ORIGINS` must include exact frontend origin.
- Do not mix hosts casually (for example `localhost` vs `127.0.0.1`) during local cookie testing.
- For cross-site production usage, set cookie flags appropriately (`Secure`, `SameSite=None`) and use HTTPS.

## 10) Quick Frontend Utility Snippet

```ts
export async function apiFetch(path: string, init: RequestInit = {}) {
  const csrf = document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrf_token='))
    ?.split('=')[1];

  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers || {});

  if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && csrf && !headers.has('X-CSRF-Token')) {
    headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }

  const res = await fetch(`http://127.0.0.1:8000${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  return res;
}
```

## 11) Existing Testing Assets You Can Reuse

- Postman collection: `docs/postman/LogOnService.postman_collection.json`
- Local Postman env: `docs/postman/LogOnService.local.postman_environment.json`

## 12) Handing This to Another Frontend Repo / Codex

Give this file and mention these integration rules explicitly:

- Use cookie auth only (no token storage in localStorage).
- Include credentials in every request.
- Attach `X-CSRF-Token` on mutating methods.
- Handle `401` with refresh flow.
- Handle MFA-required branch from login.
- Treat admin endpoints as MFA-elevated only.
