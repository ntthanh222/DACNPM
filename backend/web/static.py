"""Routes for serving the bundled frontend."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


FRONTEND_PATH = Path(__file__).resolve().parents[2] / "frontend"
router = APIRouter()


def mount_static(app) -> None:
    if not FRONTEND_PATH.exists():
        return
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_PATH / "assets")), name="assets")
    app.mount("/pages", StaticFiles(directory=str(FRONTEND_PATH / "pages")), name="pages")
    app.include_router(router)


def _file_response(filename: str, not_found: str):
    path = FRONTEND_PATH / filename
    if path.exists():
        return FileResponse(str(path))
    raise HTTPException(status_code=404, detail=not_found)


@router.get("/")
async def serve_frontend():
    index_file = FRONTEND_PATH / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return _file_response("dashboard.html", "Frontend files not found")


@router.get("/login")
@router.get("/login.html")
async def serve_login():
    return _file_response("login.html", "Login page not found")


@router.get("/dashboard")
@router.get("/dashboard.html")
async def serve_dashboard():
    return _file_response("dashboard.html", "Dashboard not found")


@router.get("/index.html")
async def serve_index_html():
    return _file_response("index.html", "Index not found")


@router.get("/favicon.ico")
async def favicon():
    for filename in ("assets/images/favicon.ico", "assets/images/default-icon.png"):
        path = FRONTEND_PATH / filename
        if path.exists():
            return FileResponse(str(path))
    return Response(status_code=204)
