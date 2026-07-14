"""Application factory for the CyberSec Assistant backend."""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.router import api_router
from backend.config import settings
from backend.core.observability import limiter, record_request
from backend.middleware.error_handler import setup_exception_handling
from backend.web.static import mount_static


def create_app() -> FastAPI:
    app = FastAPI(
        title="CyberSec Assistant API",
        description="Backend API for Cyber Security Assistant",
        version="1.0.0",
        default_response_class=JSONResponse,
    )
    setup_exception_handling(app)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-User-ID"],
    )

    @app.middleware("http")
    async def collect_prometheus_metrics(request: Request, call_next):
        start_time = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            record_request(request.method, path, status_code, time.monotonic() - start_time)

    app.include_router(api_router)
    mount_static(app)
    return app


app = create_app()
