from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse

from app.api.routes import auth_router, mfa_router, users_router
from app.core.config import settings
from app.core.redis import close_redis_client
from app.middlewares.audit_middleware import AuditMiddleware
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
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
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
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RedisRateLimiterMiddleware)

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui() -> HTMLResponse:
        swagger = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        )
        body = swagger.body.decode("utf-8")
        auto_csrf_script = """
<script>
function readCookie(name) {
  const escaped = name.replace(/[-\\/\\\\^$*+?.()|[\\]{}]/g, "\\\\$&");
  const match = document.cookie.match(new RegExp('(?:^|; )' + escaped + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

(function () {
  const originalFetch = window.fetch.bind(window);
  window.fetch = function(input, init) {
    init = init || {};
    try {
      const method = String(init.method || "GET").toUpperCase();
      if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
        const csrf = readCookie("csrf_token");
        if (csrf) {
          const headers = new Headers(init.headers || {});
          if (!headers.has("X-CSRF-Token")) {
            headers.set("X-CSRF-Token", csrf);
          }
          init.headers = headers;
        }
      }
      if (typeof init.credentials === "undefined") {
        init.credentials = "same-origin";
      }
    } catch (_) {}
    return originalFetch(input, init);
  };
})();
</script>
"""
        body = body.replace("</body>", auto_csrf_script + "\n</body>")
        response_headers = {
            key: value
            for key, value in swagger.headers.items()
            if key.lower() not in {"content-length", "content-type"}
        }
        return HTMLResponse(content=body, status_code=swagger.status_code, headers=response_headers)

    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/health", tags=["system"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "logonservice"}

    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(users_router)
    return app


app = create_app()
