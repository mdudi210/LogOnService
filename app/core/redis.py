from app.core.config import settings


def get_redis_url() -> str:
    return settings.REDIS_URL


def get_redis_client():
    import redis

    return redis.Redis.from_url(get_redis_url(), decode_responses=True)
