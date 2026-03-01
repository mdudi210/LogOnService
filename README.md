# LogOnService

Authentication and login service foundation for enterprise/fintech-grade systems.

## 1. Current Status

### Completed
- Modular project structure created under `app/` (core, models, repositories, services, api, schemas, middlewares, tests, utils).
- PostgreSQL containerized setup is ready in `utilsContainers/Postgre`.
- Redis containerized setup is ready in `utilsContainers/Redis`.
- SQLAlchemy models implemented for:
  - `users`
  - `user_credentials`
  - `user_devices`
  - `sessions`
  - `user_mfa`
  - `oauth_accounts`
  - `audit_logs`
- Alembic migration setup created and initial migration added.
- DB schema successfully created and migration version tracked (`20260227_0001`).
- Seed users created with real Argon2id password hashes:
  - `admin@test.local` / `Admin@12345`
  - `user@test.local` / `User@12345`
- FastAPI app bootstrap added with router registration.
- Basic health and scaffold routes available:
  - `GET /health`
  - `GET /auth/health`
  - `POST /auth/login` (placeholder)
  - `GET /users/health`
  - `GET /users/me` (placeholder)

### In Progress / Placeholder
- Real auth login flow in `/auth/login`.
- JWT generation/verification.
- Refresh token rotation and reuse detection.
- MFA end-to-end flow.
- Encryption provider implementation in `app/utils/encryption.py`.
- Middleware logic (rate limiting, audit middleware).
- Non-placeholder tests.

## 2. Project Layout

```text
app/
  api/
  core/
  middlewares/
  migrations/
  models/
  repositories/
  schemas/
  services/
  tests/
  utils/
utilsContainers/
  Postgre/
  Redis/
```

## 3. Local Development Setup

### 3.1 Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Start PostgreSQL

```bash
cd utilsContainers/Postgre
cp .env.example .env  # first time only
docker compose --env-file .env -f docker-compose.yaml up -d
```

### 3.3 Apply database schema

From repo root:

```bash
source .venv/bin/activate
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

### 3.4 Seed test users (admin + user)

```bash
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/10-seed-test-users.sql
```

### 3.5 Start Redis

```bash
cd utilsContainers/Redis
cp .env.example .env  # first time only
docker compose --env-file .env -f docker-compose.yaml up -d
```

### 3.6 Run API

From repo root:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

### 3.7 Run tests

```bash
source .venv/bin/activate
python -m pytest -q app/tests
```

## 4. Environment Variables

### Application
- `DATABASE_URL` (default: `postgresql+psycopg2://postgres:postgres@localhost:5432/logonservice`)
- `REDIS_URL` (default: `redis://localhost:6379/0`)

### PostgreSQL container (`utilsContainers/Postgre/.env`)
- `POSTGRES_IMAGE_TAG`
- `POSTGRES_CONTAINER_NAME`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST_PORT`
- `POSTGRES_DATA_MOUNT`

### Redis container (`utilsContainers/Redis/.env`)
- `REDIS_IMAGE_TAG`
- `REDIS_CONTAINER_NAME`
- `REDIS_HOST_PORT`
- `REDIS_PASSWORD`
- `REDIS_DATA_MOUNT`

## 5. Operational Checks

### Check PostgreSQL tables

```bash
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dt"
```

### Check seeded users

```bash
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT email, role FROM users ORDER BY email;"
```

### Check Redis health

```bash
cd utilsContainers/Redis
docker compose --env-file .env -f docker-compose.yaml exec -T redis_cache redis-cli ping
```

## 6. Production and Fintech-Grade Deployment Guidance

This repository can run locally with Docker volumes and can be moved to production with minimal config changes.

### 6.1 Data persistence strategy
- Local: use named volumes (`postgres_data`, `redis_data`) or `./data` bind mounts.
- Production: map to server/managed persistent storage paths (for example `/mnt/postgres/logonservice`, `/mnt/redis/logonservice`) or move to managed services.

### 6.2 Recommended production architecture
- Deploy API behind API Gateway + WAF.
- Use managed PostgreSQL (or HA Postgres cluster) with:
  - PITR backups
  - encrypted storage
  - restricted network access
- Use managed Redis with:
  - auth enabled
  - TLS enabled
  - persistence + replication
- Store secrets in a secret manager, not in `.env` committed files.
- Enforce TLS everywhere (internal + external where applicable).

### 6.3 Required security controls before go-live
- Replace test credentials and disable seed scripts in production.
- Enforce strong password policy and account lockout thresholds.
- Implement JWT signing key rotation.
- Implement refresh token rotation + reuse detection.
- Implement MFA challenge + recovery flow.
- Add audit logging for login, refresh, logout, lock, MFA events.
- Add rate limiting and anomaly/risk checks.
- Add structured logging + monitoring + alerting.

### 6.4 Compliance and operational requirements (fintech baseline)
- Access control: least privilege roles for DB and Redis.
- Data protection: encryption at rest + in transit.
- Auditing: immutable/reliable event logs.
- Backup and DR: tested restore procedures and RTO/RPO targets.
- SDLC: CI checks, dependency scanning, secret scanning, mandatory code review.

## 7. Next Iteration Plan

### Phase 1 (must complete next)
- Implement real `/auth/login` with DB user fetch + Argon2 verify.
- Implement JWT issue and verification utilities.
- Add auth dependency for protected routes (`/users/me`).
- Add tests for login success/failure and role claims.

### Phase 2
- Implement refresh token storage in Redis and rotation logic.
- Implement session max-age enforcement.
- Add device tracking on login.

### Phase 3
- Implement MFA (TOTP first), enrollment + challenge + recovery.
- Implement rate limiter middleware + audit middleware.

### Phase 4
- Add OAuth provider integration.
- Add risk engine scoring integration.
- Add CI/CD pipeline and deployment manifests.

## 8. Notes for New Developers

- Use `.venv` and never install project dependencies globally.
- Run `alembic upgrade head` after pulling schema changes.
- Use Docker Compose files under `utilsContainers/` for local infra.
- Treat `10-seed-test-users.sql` as dev-only data.
