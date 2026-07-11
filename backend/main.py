import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi import responses as fastapi_responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
from urllib.parse import urlparse
import re

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import profiles, chat, news, stats, chatbot, cve, auth_routes, reports
from api.v1 import admin
from config import settings
from middleware.error_handler import setup_exception_handling

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CyberSec Assistant API",
    description="Backend API for Cyber Security Assistant",
    version="1.0.0"
)

app.default_response_class = JSONResponse

# Set up global exception handling
setup_exception_handling(app)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration - using configurable origins from environment/settings
# Note: Removed development mode wildcard for security. Always use configured origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-ID"],
)

# Include routers
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
app.include_router(cve.router, prefix="/api/cve", tags=["cve"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

# Serve static frontend files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    app.mount("/pages", StaticFiles(directory=str(frontend_path / "pages")), name="pages")

    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend interface"""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            # Fallback to dashboard if index.html doesn't exist
            dashboard_file = frontend_path / "dashboard.html"
            if dashboard_file.exists():
                return FileResponse(str(dashboard_file))
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Frontend files not found. Please ensure frontend directory exists and contains index.html or dashboard.html"
                )

    # Serve individual HTML files
    @app.get("/login")
    async def serve_login():
        """Serve the login page"""
        login_file = frontend_path / "login.html"
        if login_file.exists():
            return FileResponse(str(login_file))
        else:
            raise HTTPException(status_code=404, detail="Login page not found")

    @app.get("/login.html")
    async def serve_login_html():
        """Serve the login page with .html extension"""
        login_file = frontend_path / "login.html"
        if login_file.exists():
            return FileResponse(str(login_file))
        else:
            raise HTTPException(status_code=404, detail="Login page not found")

    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the dashboard page"""
        dashboard_file = frontend_path / "dashboard.html"
        if dashboard_file.exists():
            return FileResponse(str(dashboard_file))
        else:
            raise HTTPException(status_code=404, detail="Dashboard not found")

    @app.get("/dashboard.html")
    async def serve_dashboard_html():
        """Serve the dashboard page with .html extension"""
        dashboard_file = frontend_path / "dashboard.html"
        if dashboard_file.exists():
            return FileResponse(str(dashboard_file))
        else:
            raise HTTPException(status_code=404, detail="Dashboard not found")

    @app.get("/index.html")
    async def serve_index_html():
        """Serve the index page with .html extension"""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        else:
            raise HTTPException(status_code=404, detail="Index not found")

    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon if exists"""
        favicon_path = frontend_path / "assets" / "images" / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        default_icon = frontend_path / "assets" / "images" / "default-icon.png"
        if default_icon.exists():
            return FileResponse(str(default_icon))
        # Return empty response if no favicon exists
        return Response(status_code=204)

else:
    @app.get("/")
    async def root():
        return {"message": "CyberSec Assistant API", "status": "running", "frontend": "not found"}

@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    return {"status": "healthy"}


@app.get("/api/proxy/image")
@limiter.limit("100/minute")
async def proxy_image(url: str, request: Request):
    """
    Proxy endpoint for fetching external images (e.g., from Google user content).
    This solves the Referer header issue when loading images from lh3.googleusercontent.com.

    Security: Only allows googleusercontent.com domains
    """
    # Validate URL
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Security: Only allow googleusercontent.com domains
        if not (domain == "lh3.googleusercontent.com" or
                domain.endswith(".googleusercontent.com")):
            raise HTTPException(
                status_code=403,
                detail="Domain not allowed. Only googleusercontent.com is permitted."
            )

        # Ensure HTTPS
        if parsed_url.scheme != "https":
            raise HTTPException(
                status_code=403,
                detail="Only HTTPS URLs are allowed."
            )

        # Additional security: Check for IP address bypass attempts
        if parsed_url.hostname and parsed_url.hostname.replace('.', '').isdigit():
            raise HTTPException(
                status_code=403,
                detail="IP address URLs are not allowed for security reasons."
            )

        # Validate URL path doesn't contain suspicious patterns (path traversal)
        suspicious_patterns = ['../', '..', '\\', '%2e%2e', '%5c', '%2E%2E']
        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if pattern in url_lower:
                raise HTTPException(
                    status_code=403,
                    detail=f"Suspicious URL pattern detected. Path traversal attempts are blocked."
                )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Fetch image from Google with enhanced security
    async with httpx.AsyncClient() as client:
        try:
            # Fetch without Referer header to avoid 400 error
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache"
                },
                timeout=10.0,
                follow_redirects=True,
                # Additional security: Limit response size to prevent DoS
                limits=httpx.Limits(max_read=10_000_000)  # 10MB max
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch image: HTTP {response.status_code}"
                )

            # VALIDATE: Ensure content type is actually an image
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=403,
                    detail=f"URL does not point to an image. Content-Type: {content_type}"
                )

            # Return image with proper security headers
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "X-Content-Type-Options": "nosniff",
                    "Content-Security-Policy": "default-src 'none';"
                }
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Image fetch timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch image: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    if settings.api_debug:
        uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=True)
    else:
        uvicorn.run(app, host=settings.api_host, port=settings.api_port)
