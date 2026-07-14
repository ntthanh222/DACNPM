"""System and observability endpoints."""

from fastapi import APIRouter, Request, Response

from backend.core.observability import limiter, render_metrics


router = APIRouter()


@router.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    return {"status": "healthy"}


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(
        content=render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
