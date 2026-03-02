# Redis Dev Container (Generic)

Portable local Redis setup with configurable storage and optional password.

## Setup
```bash
cd /Users/manishdudi/Desktop/LogOnService/utilsContainers/Redis
cp .env.example .env
docker compose --env-file .env -f docker-compose.yaml up -d
```

## Verify
```bash
docker compose --env-file .env -f docker-compose.yaml exec -T redis_cache redis-cli ping
```

## App Connection URL
- No password:
```bash
REDIS_URL=redis://localhost:${REDIS_HOST_PORT:-6379}/0
```
- With password:
```bash
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:${REDIS_HOST_PORT:-6379}/0
```

## Storage Modes (`REDIS_DATA_MOUNT`)
- `redis_data` (named volume, default)
- `./data` (local bind)
- `/mnt/redis/logonservice` (server path)

## Stop
```bash
docker compose --env-file .env -f docker-compose.yaml down
```
