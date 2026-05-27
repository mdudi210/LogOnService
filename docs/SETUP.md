# Local Setup

## Prerequisites
- Python 3.9+
- Docker + Docker Compose
- macOS/Linux shell (examples use `zsh`/`bash`)

## 1) Python Environment
```bash
cd /Users/manishdudi/Desktop/LogOnService
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) PostgreSQL Container
```bash
cd utilsContainers/Postgre
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 3) Redis Container
```bash
cd ../Redis
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 4) Email Container (Mailpit)
```bash
cd ../Email
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 5) Apply Migrations
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

## 6) Seed Dev Users
```bash
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/10-seed-test-users.sql
```

## 7) Run API
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
uvicorn app.main:app --reload
```

## 8) Verify
- Health: `GET http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`
- Mailpit UI: `http://localhost:8025`

## Common Commands
```bash
# run tests
python -m pytest -q app/tests

# check postgres tables
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dt"

# check redis
cd ../Redis
docker compose --env-file .env -f docker-compose.yaml exec -T redis_cache redis-cli ping

# check email inbox
cd ../Email
docker compose --env-file .env -f docker-compose.yaml logs -f
```

## Hostname Consistency Note
For cookie-based auth, avoid mixing hostnames across frontend and backend.
- Good: `localhost:3000` + `localhost:8000`
- Good: `127.0.0.1:3000` + `127.0.0.1:8000`
- Avoid: `localhost` frontend with `127.0.0.1` backend (or vice-versa)
