# PostgreSQL Dev Container (Generic)

This setup is portable for all developers and configurable via environment variables.

## 1) Create local env file

From `utilsContainers/Postgre`:

```bash
cp .env.example .env
```

## 2) Choose storage mode

In `.env`, set `POSTGRES_DATA_MOUNT`:

- `postgres_data` (default named Docker volume)
- `./data` (bind mount to your local machine)
- `/mnt/postgres/logonservice` (server path later)

## 3) Start Postgres

```bash
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 4) Apply schema (current models)

```bash
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/00-init.sql
```

## 5) Stop Postgres

```bash
docker compose --env-file .env -f docker-compose.yaml down
```

## App Database URL

```bash
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:${POSTGRES_HOST_PORT:-5432}/${POSTGRES_DB:-logonservice}
```

## Migration Standard (Industry)

- Canonical migration path is Alembic in `app/migrations`.
- Install tooling once:

```bash
python3 -m pip install alembic sqlalchemy psycopg2-binary
```

- Apply migrations:

```bash
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:${POSTGRES_HOST_PORT:-5432}/${POSTGRES_DB:-logonservice}
alembic upgrade head
```
