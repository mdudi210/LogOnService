# LogOnService

Async-first authentication and identity service built with FastAPI, PostgreSQL, and Redis.

## Update - 2026-04-01

- Added local Mailpit email server integration in Docker (`email` service) for end-to-end SMTP testing.
- Added utility email container setup under `utilsContainers/Email`.
- Added admin test endpoint `POST /users/admin/security-events/test-alert` to validate security alert email/webhook pipeline.
- Updated default/test domains to `@logonservices.local` across app code, tests, seed data, and docs.
- Added welcome email sending on new user creation (`/auth/register` and first-time Google OAuth user creation).
- Expanded security alert email delivery to support recipients from both `ALERT_EMAIL_TO` and `SECURITY_ALERT_EMAIL` (comma-separated supported).
- Updated setup/API/handoff docs and Postman assets to reflect the latest auth + email testing workflow.

## Project Overview

LogOnService provides secure authentication primitives for enterprise systems:

- Async API layer with `FastAPI`
- Async persistence with `SQLAlchemy 2.x` + `PostgreSQL`
- Stateful token/session controls with `Redis`
- Security controls: Argon2id password hashing, JWT cookies, CSRF protection, RBAC, refresh-token reuse detection, audit logging, TOTP MFA, and Email OTP MFA

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
- Email OTP MFA setup/verify and method choice at login (`totp` or `email`)
- TOTP secret encryption-at-rest (`totp_secret`)
- RBAC with admin MFA-claim enforcement
- Adaptive risk-scoring on login + high-risk blocking for users without MFA
- OAuth account link/login + Google/GitHub authorization-code callback flows
- Security alerting pipeline (audit + optional email/webhook with Slack/Discord templates)
- Session self-service APIs (`/users/me/sessions*`) for visibility and revoke controls
- Admin security observability APIs (`/users/admin/security-events`, CSV export, `/users/admin/activity`)
- Dockerized local stack (`web`, `db`, `redis`, `email`/Mailpit)
- Containerized integration tests with `testcontainers`
- CI pipeline with tests/migration checks + quality/security jobs

### Next Recommended Work

1. Add enterprise OIDC/SAML providers and hardened account-link trust policies
2. Add device fingerprint confidence scoring + impossible-travel detection
3. Route alerts to SIEM/on-call tooling and define incident SLAs
4. Add stricter CI gates for mypy/bandit/pip-audit once baseline debt is reduced
5. Expand negative-path and abuse-case security regression tests

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

If host port `6379` is already in use, set `REDIS_HOST_PORT=6380` (or any free port) in `.env`.

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
- Mailpit UI: `http://localhost:8025`

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

### `email`

- `axllent/mailpit`
- SMTP capture endpoint for local/dev testing
- SMTP: `localhost:1025`
- Inbox UI: `http://localhost:8025`

## Test Email Delivery Locally

1. Start stack:

```bash
docker compose up -d --build
```

2. Login as admin in Swagger (`/docs`) and complete MFA if prompted.
3. Trigger test alert:

```bash
curl -X POST "http://127.0.0.1:8000/users/admin/security-events/test-alert" \
  -H "accept: application/json" \
  -H "X-CSRF-Token: <csrf_token_value>" \
  --cookie "access_token=<access>; csrf_token=<csrf>"
```

4. Open Mailpit UI and verify message:
   `http://localhost:8025`

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

## Postman Smoke Collections

- Collection: [docs/postman/LogOnService.postman_collection.json](/Users/manishdudi/Desktop/LogOnService/docs/postman/LogOnService.postman_collection.json)
- Environment: [docs/postman/LogOnService.local.postman_environment.json](/Users/manishdudi/Desktop/LogOnService/docs/postman/LogOnService.local.postman_environment.json)
- Includes:
  - `Runner Smoke` (auth lifecycle)
  - `Runner Admin Security` (admin health + security events JSON/CSV assertions)

to test request limiting we can use this command on our terminal

Terminal (macos):
for i in {1..1001}; do
echo "Request #$i";
curl -X POST "http://127.0.0.1:8000/auth/login" \
 -H "accept: application/json" \
 -H "Content-Type: application/json" \
 -d '{"email_or_username":"admin@logonservices.local","password":"Admin@12345"}';
echo -e "\n------------------";
done

## QA testing

Created users:

Admin
Email: admin.qa@logonservices.local
Username: admin_qa
Password: AdminQA@12345
Role: admin
User
Email: user.qa@logonservices.local
Username: user_qa
Password: UserQA@12345
Role: user
Email test result:

Mailpit shows 2 messages delivered:
to admin.qa@logonservices.local
to user.qa@logonservices.local
