# LogOnService Frontend

Production-style React console for LogOnService backend.

## Features

- Single auth command page (`/auth`) with sign in + sign up
- OAuth sign-in via Google and GitHub
- MFA challenge flow after login (`totp` or `email`)
- User dashboard:
  - MFA setup/verify
  - View active sessions
  - Revoke one session
  - Revoke all other sessions
- Admin dashboard:
  - Org users list with role + MFA + OAuth posture
  - Security events table
  - Activity feed
  - CSV export for security events
  - Manual security test-alert trigger
  - Full user self-service controls for admin account (MFA setup/verify + session revoke controls)
- Cookie-based auth with automatic CSRF header attachment for state-changing APIs

## Run

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

App default URL: `http://127.0.0.1:5173`

Backend API URL is controlled by `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`).

## OAuth Callback Setup

For frontend-driven OAuth callback, configure provider redirect URIs to:

- Google: `http://127.0.0.1:5173/oauth/callback/google`
- GitHub: `http://127.0.0.1:5173/oauth/callback/github`

The callback page will call backend `/auth/oauth/{provider}/callback` with `code` and `state` and then route by role.
