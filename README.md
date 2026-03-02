# LogOnService

Enterprise authentication and identity provider service foundation, built with FastAPI + async SQLAlchemy + PostgreSQL + Redis.

## Documentation Index
- [Project Status](/Users/manishdudi/Desktop/LogOnService/docs/PROJECT_STATUS.md)
- [Local Setup](/Users/manishdudi/Desktop/LogOnService/docs/SETUP.md)
- [Architecture](/Users/manishdudi/Desktop/LogOnService/docs/ARCHITECTURE.md)
- [API Contract](/Users/manishdudi/Desktop/LogOnService/docs/API.md)
- [Security Model](/Users/manishdudi/Desktop/LogOnService/docs/SECURITY.md)
- [Testing Guide](/Users/manishdudi/Desktop/LogOnService/docs/TESTING.md)
- [Manual Testing Runbook](/Users/manishdudi/Desktop/LogOnService/docs/MANUAL_TESTING.md)
- [Production Guide](/Users/manishdudi/Desktop/LogOnService/docs/PRODUCTION.md)
- [Roadmap](/Users/manishdudi/Desktop/LogOnService/docs/ROADMAP.md)

## Quick Start
1. Create virtual environment and install dependencies.
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start PostgreSQL.
```bash
cd utilsContainers/Postgre
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

3. Start Redis.
```bash
cd ../Redis
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

4. Run migrations.
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/logonservice
alembic upgrade head
```

5. Seed local users.
```bash
cd utilsContainers/Postgre
docker compose --env-file .env -f docker-compose.yaml exec -T postgres_db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/10-seed-test-users.sql
```

6. Run API.
```bash
cd /Users/manishdudi/Desktop/LogOnService
source .venv/bin/activate
uvicorn app.main:app --reload
```

7. Run tests.
```bash
source .venv/bin/activate
python -m pytest -q app/tests
```
