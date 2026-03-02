# Manual Testing Runbook

This guide explains how to run the application and manually verify all implemented auth features.

## 1) Start Dependencies

### PostgreSQL
```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Postgre
cp .env.example .env 2>/dev/null || true
docker compose --env-file .env -f docker-compose.yaml up -d
```

### Redis
```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Redis
cp .env.example .env 2>/dev/null || true
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 2) Apply Migrations + Seed Data

```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

```bash
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/10-seed-test-users.sql
```

## 3) Start API

```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
uvicorn app.main:app --reload
```

Base URL used below: `http://127.0.0.1:8000`

## 4) Test Credentials (Dev Only)

- Admin: `admin@test.local` / `Admin@12345`
- User: `user@test.local` / `User@12345`

## 5) Manual API Verification (curl)

Create separate cookie jars:
```bash
rm -f /tmp/admin.cookies /tmp/user.cookies
```

### A. Health Checks
```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/auth/health
curl -i http://127.0.0.1:8000/users/health
```
Expected: `200 OK`.

### B. Login Success (Admin)
```bash
curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -c /tmp/admin.cookies \
  -d '{"email_or_username":"admin@test.local","password":"Admin@12345"}'
```
Expected:
- `200 OK`
- response JSON with `message: Login successful`
- `Set-Cookie` headers for `access_token` and `refresh_token` with `HttpOnly`

### C. Login Failure (Wrong Password)
```bash
curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email_or_username":"admin@test.local","password":"WrongPass123"}'
```
Expected: `401` with `Invalid email/username or password`.

### D. Protected Route `/users/me` (Authenticated)
```bash
curl -i http://127.0.0.1:8000/users/me -b /tmp/admin.cookies
```
Expected: `200` and user profile JSON.

### E. Protected Route `/users/me` (No Cookie)
```bash
curl -i http://127.0.0.1:8000/users/me
```
Expected: `401` (`Missing access token`).

### F. Admin Route Allowed (Admin)
```bash
curl -i http://127.0.0.1:8000/users/admin/health -b /tmp/admin.cookies
```
Expected: `200` with scope `admin`.

### G. Admin Route Forbidden (Normal User)
Login as normal user first:
```bash
curl -i -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -c /tmp/user.cookies \
  -d '{"email_or_username":"user@test.local","password":"User@12345"}'
```

Then call admin route:
```bash
curl -i http://127.0.0.1:8000/users/admin/health -b /tmp/user.cookies
```
Expected: `403` (`Insufficient permissions`).

### H. Refresh Tokens (Cookie Rotation)
```bash
curl -i -X POST http://127.0.0.1:8000/auth/refresh \
  -b /tmp/admin.cookies \
  -c /tmp/admin.cookies
```
Expected:
- `200` with `Token refresh successful`
- new `Set-Cookie` for `access_token` and `refresh_token`

### I. Refresh Without Cookie
```bash
curl -i -X POST http://127.0.0.1:8000/auth/refresh
```
Expected: `401` (`Missing refresh token`).

### J. Logout (Clear Cookies)
```bash
curl -i -X POST http://127.0.0.1:8000/auth/logout -b /tmp/admin.cookies -c /tmp/admin.cookies
```
Expected: `200` and cookie clearing headers (`Max-Age=0`).

### K. Verify Logged Out
```bash
curl -i http://127.0.0.1:8000/users/me -b /tmp/admin.cookies
```
Expected: `401`.

## 6) DB Validation Checks (Optional)

```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT email, role FROM users ORDER BY email;"
```

```bash
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT user_id, hash_algorithm, password_salt IS NOT NULL AS has_salt FROM user_credentials;"
```

## 7) Automated Test Suite

```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
python -m pytest -q app/tests
```

## 8) Shutdown

```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml down

cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Redis
docker compose --env-file .env -f docker-compose.yaml down
```
