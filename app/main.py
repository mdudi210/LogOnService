from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth_router, users_router
from app.core.config import settings
from app.core.redis import close_redis_client
from app.middlewares.rate_limiter import RedisRateLimiterMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await close_redis_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="LogOnService Auth API",
        version="0.1.0",
        description="Authentication and authorization service",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )
    app.add_middleware(RedisRateLimiterMiddleware)

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "logonservice"}

    app.include_router(auth_router)
    app.include_router(users_router)
    return app


app = create_app()
