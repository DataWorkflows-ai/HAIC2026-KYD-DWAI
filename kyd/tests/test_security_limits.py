"""Rate limits, the daily LLM budget and browser security headers (app/security.py)."""
import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import security
from app.agent import orchestrator
from app.main import app
from app.security import DailyBudget, Window

c = TestClient(app)


def test_window_allows_up_to_limit_then_waits():
    w = Window(2, 60)
    assert w.hit("a", 0) == 0 and w.hit("a", 1) == 0
    assert w.hit("a", 2) == 58
    assert w.hit("b", 2) == 0                     # other clients are unaffected
    assert w.hit("a", 61) == 0                    # the oldest hit has left the window


def test_ask_is_rate_limited_per_client(monkeypatch):
    monkeypatch.setattr(security, "ASK_MINUTE", Window(1, 60))
    h = {"cf-connecting-ip": "203.0.113.7"}
    q = {"question": "Which party will win HD 5?"}
    assert c.post("/api/agent/ask", json=q, headers=h).status_code == 200
    r = c.post("/api/agent/ask", json=q, headers=h)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0 and "wait" in r.json()["detail"]
    assert c.post("/api/agent/ask", json=q, headers={"cf-connecting-ip": "203.0.113.8"}).status_code == 200


def test_data_endpoints_limited_but_health_never(monkeypatch):
    monkeypatch.setattr(security, "API_LIMIT", Window(1, 60))
    h = {"x-forwarded-for": "198.51.100.4, 10.0.0.1"}
    assert c.get("/api/indicators", headers=h).status_code == 200
    assert c.get("/api/indicators", headers=h).status_code == 429
    assert all(c.get("/api/health", headers=h).status_code == 200 for _ in range(3))


def test_llm_budget_falls_back_to_templates(monkeypatch):
    monkeypatch.setattr(orchestrator, "settings", lambda: SimpleNamespace(llm_provider="anthropic"))
    monkeypatch.setattr(orchestrator, "LLM_BUDGET", DailyBudget(0))
    a = asyncio.run(orchestrator.ask("What is the uninsurance rate in house district 12?", None))
    assert a.route == "S1" and "llm_daily_limit" in a.escalation_reasons and "[obs:" in a.text


def test_daily_budget_counts():
    b = DailyBudget(2)
    assert [b.take(), b.take(), b.take()] == [True, True, False] and b.status()["used_today"] == 2


def test_security_headers_and_csp():
    r = c.get("/api/indicators")
    for k in ("x-content-type-options", "x-frame-options", "referrer-policy", "strict-transport-security"):
        assert k in r.headers
    csp = r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp and "https://js.arcgis.com" in csp and "object-src 'none'" in csp
    assert "content-security-policy" not in c.get("/docs").headers   # Swagger UI loads from a CDN


def test_cors_does_not_allow_other_origins():
    r = c.options("/api/agent/ask", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"
