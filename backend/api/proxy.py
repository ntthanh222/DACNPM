"""Safe proxy endpoints for externally hosted assets."""

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from urllib.parse import urlparse

from backend.core.observability import limiter


router = APIRouter()
MAX_PROXY_IMAGE_BYTES = 10_000_000


@router.get("/image")
@limiter.limit("100/minute")
async def proxy_image(url: str, request: Request):
    """Proxy an image only from HTTPS googleusercontent.com URLs."""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if not (domain == "lh3.googleusercontent.com" or domain.endswith(".googleusercontent.com")):
            raise HTTPException(status_code=403, detail="Domain not allowed. Only googleusercontent.com is permitted.")
        if parsed_url.scheme != "https":
            raise HTTPException(status_code=403, detail="Only HTTPS URLs are allowed.")
        if parsed_url.hostname and parsed_url.hostname.replace('.', '').isdigit():
            raise HTTPException(status_code=403, detail="IP address URLs are not allowed for security reasons.")
        if any(pattern in url.lower() for pattern in ('../', '..\\', '%2e%2e', '%5c', '%2E%2E')):
            raise HTTPException(status_code=403, detail="Suspicious URL pattern detected. Path traversal attempts are blocked.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                },
                timeout=10.0,
                follow_redirects=True,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch image: HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(status_code=403, detail=f"URL does not point to an image. Content-Type: {content_type}")
            if len(response.content) > MAX_PROXY_IMAGE_BYTES:
                raise HTTPException(status_code=413, detail="Image is too large. Maximum size is 10MB.")
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Content-Type-Options": "nosniff",
                    "Content-Security-Policy": "default-src 'none';",
                },
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Image fetch timeout")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch image: {exc}")
