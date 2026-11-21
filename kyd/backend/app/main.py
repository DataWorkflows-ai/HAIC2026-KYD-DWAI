"""KYD API. Run with: uvicorn app.main:app --port 8060 (from backend/)."""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from . import accounts
from .auth import signed_in
from .config import settings
from .routers import api
from .security import SecurityMiddleware

app = FastAPI(title="Know Your District API", version="1.0.0",
              description="HAIC 2026 Challenge 1. Every figure is an Observation with a citation.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "Authorization"])
app.add_middleware(SecurityMiddleware)
app.include_router(api)
app.include_router(accounts.auth_api)
app.include_router(accounts.api, dependencies=[Depends(signed_in)])

_dist = settings().frontend_dist
for _sub in ("assets", "geo"):
    if (_dist / _sub).exists():
        app.mount(f"/{_sub}", StaticFiles(directory=_dist / _sub), name=_sub)


@app.get("/", include_in_schema=False)
def root():
    idx = _dist / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return HTMLResponse("<p>Frontend not built. Run <code>cd frontend && npm run build</code>. API docs at "
                        "<a href='/docs'>/docs</a>.</p>")


# Shareable links (/house-22, /senate-12/map, /state/rankings) are app routes: serve the same page.
@app.get("/{slug:path}", include_in_schema=False)
def app_route(slug: str):
    import re
    if re.fullmatch(r"(?:house|senate|hd|sd)-?\d{1,2}(?:/[a-z]+)?/?|state(?:/[a-z]+)?/?|hi(?:/[a-z]+)?/?", slug, re.I):
        return root()
    from fastapi import HTTPException
    raise HTTPException(status_code=404)
