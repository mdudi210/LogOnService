# Alembic Migrations

## Prerequisites
- PostgreSQL running
- `DATABASE_URL` using async driver (`postgresql+asyncpg://...`)

## Apply latest migration
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

## Check current revision
```bash
alembic current
```

## Create new migration
```bash
alembic revision --autogenerate -m "describe change"
```

## Migration Notes
- `20260227_0001`: initial auth schema
- `20260302_0002`: adds `password_salt` to `user_credentials`
