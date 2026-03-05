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
