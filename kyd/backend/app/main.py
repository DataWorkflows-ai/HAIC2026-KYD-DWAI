"""KYD API. Run with: uvicorn app.main:app --port 8060 (from backend/)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .routers import api

app = FastAPI(title="Know Your District API", version="0.1.0",
              description="HAIC 2026 Challenge 1. Every figure is an Observation with a citation.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(api)

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
