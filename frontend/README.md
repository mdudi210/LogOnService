# LogOnService Frontend

Frontend console for LogOnService with separate user and admin dashboards.

All frontend-related assets are contained in this folder:
- source code
- env files
- Docker setup
- docs

## Tech Stack
- React 18 + TypeScript
- Vite
- React Router
- Cookie-based API auth with CSRF header injection

## Features Implemented
- Login with optional MFA completion flow (`/auth/login` + `/auth/login/mfa`)
- User dashboard:
  - Overview
  - Session listing with `is_current` marker
  - Revoke single session
  - Revoke other sessions
  - Change password
  - MFA setup + verify
- Admin dashboard:
  - Security event monitor (`/users/admin/security-events`)
  - Feature configuration panel (frontend-ready toggles using local storage placeholders)

## Folder Structure
```
frontend/
  src/
    app/            # Auth context + router
    components/     # Shared UI shell/guards/banners
    features/
      auth/         # Login + MFA step
      user/         # User pages (overview/sessions/security)
      admin/        # Admin pages (events/config)
    lib/            # API client + cookie helpers
    styles/         # Global styling
    types/          # TS contracts
  docs/
    ARCHITECTURE.md
  Dockerfile
  Dockerfile.dev
  docker-compose.yml
```

## Environment Variables
Create/update `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

Backend requirement:
- Backend CORS must include frontend origin (`http://127.0.0.1:3000` and/or `http://localhost:3000`).
- Use consistent hostnames between frontend/backend (`localhost` with `localhost`, or `127.0.0.1` with `127.0.0.1`) to avoid cookie/site mismatch.

## Troubleshooting Login
- Seeing `{\"detail\":\"Missing access token\"}` on first load is expected before login because frontend checks `/users/me`.
- If it appears even after successful login:
  1. Ensure backend is reachable at `VITE_API_BASE_URL`.
  2. Ensure frontend and backend hostname are consistent (no mix of `localhost` and `127.0.0.1`).
  3. Ensure backend `ALLOWED_CORS_ORIGINS` includes your frontend origin.

## Run (Manual)
```bash
cd frontend
npm install
npm run dev
```
Frontend URL: `http://127.0.0.1:3000`

## Run (Docker Dev)
```bash
cd frontend
docker compose up --build frontend-dev
```
Frontend URL: `http://127.0.0.1:3000`

## Run (Docker Prod Preview)
```bash
cd frontend
docker compose --profile prod up --build frontend-prod
```
Frontend URL: `http://127.0.0.1:8080`

## Operational Flow (E2E)
1. Login from `/login`
2. If MFA required, submit code in second step
3. Land on overview page
4. Manage sessions from `/sessions`
5. Manage password/MFA from `/security`
6. For admin role, monitor events at `/admin/events`

## Future-ready Admin Extension Plan
- Replace local feature toggles with backend config APIs
- Add admin controls for SMTP/security alert settings
- Add user lifecycle controls (lock/unlock, forced logout, policy templates)
