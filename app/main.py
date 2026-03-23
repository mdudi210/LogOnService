from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.routes import auth_router, mfa_router, users_router
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
        docs_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            settings.CSRF_HEADER_NAME,
        ],
    )
    app.add_middleware(RedisRateLimiterMiddleware)

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        html = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_ui_parameters={
                "persistAuthorization": True,
                "displayRequestDuration": True,
            },
        )
        csrf_injector = f"""
<script>
window.addEventListener("load", function () {{
  if (!window.ui) return;
  window.ui.getConfigs().requestInterceptor = function (req) {{
    const method = (req.method || "").toUpperCase();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) {{
      return req;
    }}
    const csrfCookieName = "{settings.CSRF_COOKIE_NAME}";
    const csrfHeaderName = "{settings.CSRF_HEADER_NAME}";
    const cookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith(csrfCookieName + "="));
    if (cookie) {{
      const csrfValue = decodeURIComponent(cookie.split("=")[1] || "");
      if (csrfValue) {{
        req.headers = req.headers || {{}};
        req.headers[csrfHeaderName] = csrfValue;
      }}
    }}
    return req;
  }};
}});
</script>
"""
        content = html.body.decode("utf-8").replace("</body>", f"{csrf_injector}</body>")
        headers = dict(html.headers)
        headers.pop("content-length", None)
        return HTMLResponse(
            content=content,
            status_code=html.status_code,
            headers=headers,
        )

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "logonservice"}

    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(users_router)
    return app


app = create_app()
