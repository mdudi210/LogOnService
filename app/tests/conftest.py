import asyncio
import os
from typing import Optional

from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

_postgres: Optional[PostgresContainer] = None
_redis: Optional[RedisContainer] = None


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def pytest_sessionstart(session) -> None:
    global _postgres, _redis

    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

    _postgres = PostgresContainer("postgres:16-alpine", username="postgres", password="postgres", dbname="logonservice")
    _redis = RedisContainer("redis:7-alpine")

    _postgres.start()
    _redis.start()

    database_url = _to_asyncpg_url(_postgres.get_connection_url())
    redis_host = _redis.get_container_host_ip()
    redis_port = _redis.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"

    os.environ["DATABASE_URL"] = database_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["PYTEST_USE_NULL_POOL"] = "1"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


def pytest_sessionfinish(session, exitstatus) -> None:
    try:
        from app.core.database import engine
        from app.core.redis import close_redis_client

        asyncio.run(close_redis_client())
        asyncio.run(engine.dispose())
    except Exception:
        pass

    global _postgres, _redis
    if _redis is not None:
        _redis.stop()
        _redis = None
    if _postgres is not None:
        _postgres.stop()
        _postgres = None
