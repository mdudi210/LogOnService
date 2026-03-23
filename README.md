# LogOnService

Async-first authentication and identity service built with FastAPI, PostgreSQL, and Redis.

## Project Overview
LogOnService provides secure authentication primitives for enterprise systems:
- Async API layer with `FastAPI`
- Async persistence with `SQLAlchemy 2.x` + `PostgreSQL`
- Stateful token/session controls with `Redis`
- Security controls: Argon2id password hashing, JWT cookies, CSRF protection, RBAC, refresh-token reuse detection, audit logging, and TOTP MFA flow

## Architecture
- `app/main.py`: app bootstrap, CORS, rate limiter middleware, routers
- `app/api/routes/*`: auth, users, mfa endpoints
- `app/services/*`: auth logic, token/session management, TOTP, email
- `app/repositories/*`: async DB data access
- `app/migrations/*`: Alembic migrations
- `app/tests/*`: API + integration tests (real DB/Redis containers via testcontainers)

## Current Status
### Completed
- Async SQLAlchemy engine/session stack with pooling
- Argon2id + per-user salt password verification
- JWT access/refresh cookies (HttpOnly) + refresh rotation
- Redis-backed refresh `jti` persistence and revoke-all behavior
- Refresh token reuse detection + forensic audit log writes
- CSRF double-submit-cookie protection for mutating endpoints
- Registration and password-change flows
- TOTP setup/verify and two-step login (`/auth/login` + `/auth/login/mfa`)
- RBAC with admin MFA-claim enforcement
- Dockerized local stack (`web`, `db`, `redis`)
- Containerized integration tests with `testcontainers`

### Next Recommended Work
1. Encrypt `totp_secret` at rest (currently plaintext)
2. Add CI pipeline (lint, tests, migration checks)
3. Add observability/security alerting (audit events, replay alerts)
4. Harden production profile (cookie/domain/TLS defaults, secrets management)
5. Expand test coverage for negative/security edge cases

---

## API Cookie Requirements (Team Reference)
The API uses cookie-based auth. For state-changing routes, CSRF double-submit is required.

| Route | Method | Required Cookies | Required Header | Notes |
|---|---|---|---|---|
| `/auth/login` | POST | none | none | Sets `access_token`, `refresh_token`, `csrf_token` |
| `/auth/login/mfa` | POST | none | none | Sets `access_token`, `refresh_token`, `csrf_token` after MFA verification |
| `/auth/register` | POST | none | none | Public route |
| `/auth/refresh` | POST | `refresh_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Rotates refresh token pair |
| `/auth/logout` | POST | `csrf_token` (and optionally `refresh_token`) | `X-CSRF-Token` (must match cookie) | Clears auth cookies even if refresh is missing/invalid |
| `/auth/logout-all` | POST | `access_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Revokes all user sessions |
| `/users/me` | GET | `access_token` | none | Returns current user |
| `/users/admin/health` | GET | `access_token` | none | Admin role required (+ MFA claim for admin) |
| `/users/admin/security-events` | GET | `access_token` | none | Admin observability endpoint for recent audit/security events |
| `/users/me/sessions` | GET | `access_token`, `refresh_token` | none | Lists active sessions and marks `is_current` from refresh JTI |
| `/users/me/sessions/{jti}` | DELETE | `access_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Revokes one session by JTI (owner only) |
| `/users/me/sessions` | DELETE | `access_token`, `refresh_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Revokes all other sessions, keeps current session |
| `/users/me/change-password` | POST | `access_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Invalidates other sessions and rotates cookies |
| `/mfa/setup` | POST | `access_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Generates TOTP secret |
| `/mfa/verify` | POST | `access_token`, `csrf_token` | `X-CSRF-Token` (must match cookie) | Enables MFA |

Notes:
- Swagger now auto-attaches `X-CSRF-Token` from `csrf_token` cookie for `POST/PUT/PATCH/DELETE`.
- OpenAPI displays cookie/header requirements through route dependencies.
- Security events are persisted in `audit_logs` and emitted as structured logs (`app.security.events` logger).
- Optional email alerts can be enabled with `SECURITY_ALERTS_ENABLED=true` + `SECURITY_ALERT_EMAIL`.

---

## Setup Option 1: Manual (Local Python + Local Services)

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker (optional, only if you want to run DB/Redis in containers)

### 1. Clone and install deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
```
Update `.env` values as needed (DB, Redis, JWT secrets).

### 3. Start PostgreSQL and Redis
Use your local installs, or use your existing utility containers:
```bash
docker compose -f utilsContainers/Postgre/docker-compose.yaml --env-file utilsContainers/Postgre/.env up -d
docker compose -f utilsContainers/Redis/docker-compose.yaml --env-file utilsContainers/Redis/.env up -d
```

### 4. Run migrations
```bash
alembic upgrade head
```

### 5. Run API
```bash
uvicorn app.main:app --reload
```

### 6. Run tests
```bash
python -m pytest -q app/tests
```

---

## Setup Option 2: Docker Compose (Recommended for team onboarding)

### Prerequisites
- Docker Desktop / Docker Engine running

### 1. Configure env
```bash
cp .env.example .env
```

### 2. Build and start stack
```bash
docker compose up -d --build
```

### 3. Apply migrations
```bash
docker compose exec web alembic upgrade head
```

### 4. Access API
- App: `http://localhost:8000`
- Health: `http://localhost:8000/health`

### 5. Run tests
From host:
```bash
python -m pytest -q app/tests
```
Inside container:
```bash
docker compose exec web python -m pytest -q app/tests
```

---

## Docker Services
### `web`
- Multi-stage build from [Dockerfile](/Users/manishdudi/Desktop/LogOnService/Dockerfile)
- Runs as non-root user
- Exposes `8000`
- Depends on healthy `db` and `redis`
- Bind-mount enabled for local dev reload

### `db`
- `postgres:16-alpine`
- Persistent volume: `postgres_data`
- Health check: `pg_isready`

### `redis`
- `redis:7-alpine`
- Persistent volume: `redis_data`
- Health check: `redis-cli ping`

## Common Commands
```bash
# stop stack
docker compose down

# stop and remove volumes
docker compose down -v

# rebuild only web
docker compose build web

# tail web logs
docker compose logs -f web
```

## Frontend Module
- Frontend lives fully under: `frontend/`
- Frontend docs: [frontend/README.md](/Users/manishdudi/Desktop/LogOnService/frontend/README.md)
- Frontend architecture: [ARCHITECTURE.md](/Users/manishdudi/Desktop/LogOnService/frontend/docs/ARCHITECTURE.md)

Quick start:
```bash
cd frontend
npm install
npm run dev
```

Docker dev:
```bash
cd frontend
docker compose up --build frontend-dev
```

## CI Pipeline
- GitHub Actions workflow: [.github/workflows/ci.yml](/Users/manishdudi/Desktop/LogOnService/.github/workflows/ci.yml)
- Runs on push and pull requests
- Installs dependencies, verifies Docker, runs `pytest -q app/tests`

## Security Observability
- `AuditRepository.create_event(...)` now also emits a structured security log entry.
- Config-driven alerting (email via SMTP) for selected event types:
  - `SECURITY_ALERTS_ENABLED`
  - `SECURITY_ALERT_EMAIL`
  - `SECURITY_ALERT_EVENT_TYPES` (comma-separated)
