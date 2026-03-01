from fastapi import FastAPI

from app.api.routes import auth_router, users_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="LogOnService Auth API",
        version="0.1.0",
        description="Authentication and authorization service",
    )

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "logonservice"}

    app.include_router(auth_router)
    app.include_router(users_router)
    return app


app = create_app()
