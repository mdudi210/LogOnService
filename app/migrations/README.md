# Alembic Migrations

Use these commands from repository root:

```bash
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

Create new migration:

```bash
alembic revision --autogenerate -m "describe change"
```
