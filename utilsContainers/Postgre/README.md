# PostgreSQL Dev Container (Generic)

Portable local PostgreSQL setup with configurable storage and credentials.

## Setup
```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Postgre
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

## Apply Schema via Alembic (Recommended)
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:${POSTGRES_HOST_PORT:-5432}/${POSTGRES_DB:-logonservice}
alembic upgrade head
```

## Seed Dev Users
```bash
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/10-seed-test-users.sql
```

## Verify
```bash
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\dt"
```

## Storage Modes (`POSTGRES_DATA_MOUNT`)
- `postgres_data` (named volume, default)
- `./data` (local bind)
- `/mnt/postgres/logonservice` (server path)

## Stop
```bash
docker compose --env-file .env -f docker-compose.yaml down
```
