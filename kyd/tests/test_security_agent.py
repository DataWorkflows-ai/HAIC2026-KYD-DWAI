"""Fixes 1–5 from the Nov 2026 review: auth, guardrail scope, gazetteer, S2 failure, unsupported numbers.
Run from backend/: pytest ../tests"""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent import orchestrator, system1, system2
from app.auth import mint
from app.config import settings
from app.main import app

c = TestClient(app)


@pytest.fixture
def secret():
    s = settings()
    old = (s.auth_secret, s.trust_proxy_headers)
    s.auth_secret, s.trust_proxy_headers = "test-secret", False
    yield s
    s.auth_secret, s.trust_proxy_headers = old


# 1. auth ────────────────────────────────────────────────────────────────────
def test_spoofed_role_header_is_ignored(secret):
    assert c.get("/api/audit/verify", headers={"x-kyd-user": "x", "x-kyd-role": "auditor"}).status_code == 403
    assert c.get("/api/me", headers={"x-kyd-role": "admin"}).json() == {"user": "anonymous", "role": "viewer"}


def test_signed_token_grants_role(secret):
    tok = mint("aud.1", "auditor")
    r = c.get("/api/audit/verify", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json()["ok"]
    assert c.get("/api/me", headers={"Authorization": f"Bearer {tok}"}).json()["role"] == "auditor"


def test_tampered_or_expired_token_rejected(secret):
    tok = mint("v", "viewer")
    payload, sig = tok.split(".")
    forged = mint("v", "admin", secret="other-secret").split(".")[0] + "." + sig
    assert c.get("/api/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    expired = mint("v", "viewer", ttl_seconds=-10)
    assert c.get("/api/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_viewer_token_cannot_verify_audit(secret):
    tok = mint("v", "viewer")
    assert c.get("/api/audit/verify", headers={"Authorization": f"Bearer {tok}"}).status_code == 403


def test_proxy_headers_only_when_enabled(secret):
    secret.trust_proxy_headers = True
    h = {"x-kyd-user": "sso.user", "x-kyd-role": "auditor"}
    assert c.get("/api/me", headers=h).json() == {"user": "sso.user", "role": "auditor"}
    assert c.get("/api/me", headers={"x-kyd-user": "u", "x-kyd-role": "root"}).json()["role"] == "viewer"


# 2. guardrail scope ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("q", ["How did the HD 22 representative vote on SB 123?",
                               "Show the voting record for Senate District 9",
                               "Who are the elected officials for House District 5?"])
def test_voting_records_allowed(q):
    assert system1.route(q).decision != "REFUSE"


@pytest.mark.parametrize("q", ["Which candidate should win SD 9?", "Who should I vote for in HD 22?",
                               "Is HD 5 a swing district for Democrats?", "Help me plan a re-election campaign",
                               "Who in HD 5 receives SNAP?"])
def test_electoral_and_individual_still_refused(q):
    assert system1.route(q).decision == "REFUSE"


# 3. gazetteer ───────────────────────────────────────────────────────────────
def test_place_with_dominant_district_resolves():
    rt = system1.route("Profile of Haʻikū")
    assert rt.geo_ids == ["HD-13"] and rt.decision == "S1"


def test_zip_resolves():
    assert system1.route("demographics for 96744").geo_ids == ["HD-48"]


def test_okina_and_kahako_place():
    assert system1.route("Kāneʻohe overview").places[0]["name"] == "Kaneohe"


def test_longest_alias_wins():
    names = [p["name"] for p in system1.route("Waipio Acres population").places]
    assert names == ["Waipio Acres"]


def test_senate_chamber_from_wording():
    rt = system1.route("Senate profile for Haiku")
    assert rt.geo_ids and rt.geo_ids[0].startswith("SD-")


def test_split_place_asks_which_district_without_llm():
    a = c.post("/api/agent/ask", json={"question": "Profile of Kāneʻohe"}).json()
    assert "place_spans_districts" in a["escalation_reasons"]
    assert "Do you mean" in a["text"] and "House District 49" in a["text"]


# 4. S2 failure never becomes a 500 ─────────────────────────────────────────
def test_s2_http_error_falls_back(monkeypatch):
    async def boom(*a, **k):
        raise httpx.ConnectTimeout("llm down")
    monkeypatch.setattr(system2, "run", boom)
    r = c.post("/api/agent/ask", json={"question": "Tell me about HD 22 and HD 23 and HD 24"})
    assert r.status_code == 200 and "s2_error" in r.json()["escalation_reasons"]
    r = c.post("/api/agent/ask", json={"question": "What should we know about House District 22"})
    assert r.status_code == 200 and r.json()["observations"]


# 5. unsupported numbers are removed ────────────────────────────────────────
def test_redact_unsupported():
    obs = [{"obs_id": "x1", "value": 84512.0, "moe": 3100.0}]
    text = "Median income is $84,512 [obs:x1] in District 22 (2024), about 12.7% higher than 2019."
    out, bad = system2.redact_unsupported(text, obs)
    assert bad == ["12.7%"] and "12.7" not in out and "$84,512" in out and system2.REDACTED in out


def test_s2_answer_with_invented_number_is_redacted(monkeypatch):
    from app.services.repo import repo
    o = repo().observations(["HD-22"], ["pct_below_fpl"])[0].model_dump()

    async def fake(q, hint):
        return f"Poverty is {o['value']}% [obs:{o['obs_id']}], up from 99.9% before.", [o], []
    monkeypatch.setattr(system2, "run", fake)
    a = asyncio.run(orchestrator.ask("how does HD 22 compare with others nearby on things", None))
    assert "99.9" not in a.text and f"{o['value']}%" in a.text and "unsupported_numbers_removed" in a.escalation_reasons
