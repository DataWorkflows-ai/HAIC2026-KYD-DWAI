"""Abuse limits and browser security headers.

Rate limits are per client, in memory, for one server process (Render runs one). The client is the
CF-Connecting-IP header that Cloudflare sets in front of Render, else the first X-Forwarded-For hop, else the
socket address. A spoofed header only moves a caller to another bucket; the daily LLM budget still caps spend.
"""
from __future__ import annotations
import threading
import time
from collections import deque
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

# ArcGIS (map SDK, Hawaiʻi boundary service, imagery) is the only third-party code or data the app loads.
ARCGIS = ("https://js.arcgis.com https://*.arcgis.com https://*.arcgisonline.com https://geodata.hawaii.gov"
          " https://*.tile.openstreetmap.org")
CSP = "; ".join([
    "default-src 'self'",
    # ArcGIS compiles Arcade label and renderer expressions at run time, which needs 'unsafe-eval'.
    "script-src 'self' blob: https://js.arcgis.com 'unsafe-eval' 'wasm-unsafe-eval'",
    "style-src 'self' 'unsafe-inline' https://js.arcgis.com",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data: https://js.arcgis.com",
    f"connect-src 'self' blob: data: {ARCGIS}",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}
DOCS = ("/docs", "/redoc")                     # Swagger UI and ReDoc load their scripts from a CDN


def client_key(req: Request) -> str:
    h = req.headers
    if ip := h.get("cf-connecting-ip"):
        return ip.strip()
    if fwd := h.get("x-forwarded-for"):
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


class Window:
    """Sliding-window counter: at most `limit` events per `seconds` for each key."""
    MAX_KEYS = 50_000

    def __init__(self, limit: int, seconds: float):
        self.limit, self.seconds = limit, seconds
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, now: float | None = None) -> float:
        """Record one event. Returns 0 if allowed, else the seconds until the next one is."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if len(self._hits) > self.MAX_KEYS:
                self._hits.clear()
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - self.seconds:
                q.popleft()
            if len(q) >= self.limit:
                return q[0] + self.seconds - now
            q.append(now)
            return 0.0


class DailyBudget:
    """At most `limit` LLM calls per UTC day across all callers. Over budget, answers fall back to templates."""

    def __init__(self, limit: int):
        self.limit, self.used, self.day = limit, 0, ""
        self._lock = threading.Lock()

    def take(self) -> bool:
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            if today != self.day:
                self.day, self.used = today, 0
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

    def status(self) -> dict:
        return {"limit": self.limit, "used_today": self.used if self.day == datetime.now(timezone.utc).date().isoformat() else 0}


_s = settings()
API_LIMIT = Window(_s.rate_api_per_minute, 60)
ASK_MINUTE = Window(_s.rate_ask_per_minute, 60)
ASK_DAY = Window(_s.rate_ask_per_day, 86400)
LLM_BUDGET = DailyBudget(_s.llm_daily_calls)


def _too_many(wait: float, what: str) -> JSONResponse:
    return JSONResponse({"detail": f"Too many {what}. Please wait about {max(1, round(wait))} seconds and try again."},
                        status_code=429, headers={"Retry-After": str(max(1, round(wait)))})


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, req: Request, call_next):
        path = req.url.path
        if path.startswith("/api/") and path != "/api/health":
            key = client_key(req)
            if path == "/api/agent/ask" and req.method == "POST":
                for w, what in ((ASK_MINUTE, "questions this minute"), (ASK_DAY, "questions today")):
                    if wait := w.hit(key):
                        return _too_many(wait, what)
            elif wait := API_LIMIT.hit(key):
                return _too_many(wait, "requests")
        resp = await call_next(req)
        for k, v in HEADERS.items():
            resp.headers.setdefault(k, v)
        mode = settings().csp_mode
        if mode != "off" and not path.startswith(DOCS):
            resp.headers.setdefault("Content-Security-Policy-Report-Only" if mode == "report" else
                                    "Content-Security-Policy", CSP)
        return resp
