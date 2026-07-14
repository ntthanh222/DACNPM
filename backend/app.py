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
    """
    Initializes and configures the FastAPI application instance.

    This factory function sets up:
    1. Exception handling routines.
    2. Rate limiting state and handler (slowapi).
    3. CORS (Cross-Origin Resource Sharing) middleware to allow safe cross-origin web access.
    4. HTTP middleware for Prometheus latency and request tracking telemetry.
    5. API router mappings.
    6. Mount points for frontend static files.

    Returns:
        FastAPI: The fully configured FastAPI application.
    """
    app = FastAPI(
        title="CyberSec Assistant API",
        description="Backend API for Cyber Security Assistant",
        version="1.0.0",
        default_response_class=JSONResponse,
    )
    
    # Configure global exception handers (e.g. database errors, general exceptions)
    setup_exception_handling(app)
    
    # Initialize slowapi rate limiter configuration
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-User-ID"],
    )

    @app.middleware("http")
    async def collect_prometheus_metrics(request: Request, call_next):
        """
        HTTP middleware that measures request duration (latency) and records
        the request statistics to Prometheus metrics.
        """
        start_time = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # Determine the API path or fallback to raw URL path if route is not matched
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            
            # Record the request method, route, status code, and latency in Prometheus histogram
            record_request(request.method, path, status_code, time.monotonic() - start_time)

    # Register business routes
    app.include_router(api_router)
    
    # Mount frontend static folders (/assets, /pages, /dashboard, etc.)
    mount_static(app)
    return app


# Create the global FastAPI app instance
app = create_app()
