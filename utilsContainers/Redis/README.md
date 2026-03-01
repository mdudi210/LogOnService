# Redis Dev Container (Generic)

This setup is portable for all developers and configurable via environment variables.

## 1) Create local env file

From `utilsContainers/Redis`:

```bash
cp .env.example .env
```

## 2) Choose storage mode

In `.env`, set `REDIS_DATA_MOUNT`:

- `redis_data` (default named Docker volume)
- `./data` (bind mount to your local machine)
- `/mnt/redis/logonservice` (server path later)

## 3) Start Redis

```bash
docker compose --env-file .env -f docker-compose.yaml up -d
```

## 4) Stop Redis

```bash
docker compose --env-file .env -f docker-compose.yaml down
```

## 5) Verify Redis

```bash
docker compose --env-file .env -f docker-compose.yaml exec -T redis_cache redis-cli ping
```

## App Redis URL

Without password:

```bash
REDIS_URL=redis://localhost:${REDIS_HOST_PORT:-6379}/0
```

With password:

```bash
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:${REDIS_HOST_PORT:-6379}/0
```
