import time
from typing import Callable
from typing import Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.redis import RedisError, close_redis_client, get_redis_client


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    """Global fixed-window rate limiter backed by Redis.

    This works across multiple ASGI workers/instances.
    """

    def __init__(
        self, app, max_requests: Optional[int] = None, window_seconds: Optional[int] = None
    ):
        super().__init__(app)
        self.max_requests = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.key_prefix = settings.RATE_LIMIT_KEY_PREFIX

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        window = int(time.time()) // self.window_seconds
        key = f"{self.key_prefix}:{client_host}:{window}"

        current = await self._increment_window_counter(key)
        if current is None:
            # Fail-open strategy to preserve availability if Redis is unavailable.
            return await call_next(request)

        if current > self.max_requests:
            retry_after = self.window_seconds
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(self.max_requests - current, 0))
        return response

    async def _increment_window_counter(self, key: str) -> Optional[int]:
        """Increment rate-limit counter with one recovery attempt for stale async clients."""
        for attempt in range(2):
            try:
                redis_conn = get_redis_client()
                current = await redis_conn.incr(key)
                if current == 1:
                    await redis_conn.expire(key, self.window_seconds)
                return int(current)
            except (RedisError, RuntimeError):
                if attempt == 0:
                    await close_redis_client()
                    continue
                return None
        return None
