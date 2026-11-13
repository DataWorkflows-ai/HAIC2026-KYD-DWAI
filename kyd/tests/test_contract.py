"""Run from backend/: pytest ../tests"""
import re
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/api/health").json()["ok"]


def test_every_figure_has_citation():
    p = c.get("/api/districts/HD-22").json()
    for o in p["observations"]:
        assert o["obs_id"] and o["source_id"] and o["vintage"]
        assert c.get(f"/api/sources/observation/{o['obs_id']}").status_code == 200


def test_guardrails_refuse():
    for q in ["Who in HD 5 receives SNAP?", "Which candidate should win SD 9?"]:
        assert c.post("/api/agent/ask", json={"question": q}).json()["route"] == "REFUSED"


def test_s1_numbers_are_cited():
    a = c.post("/api/agent/ask", json={"question": "Profile of House District 22"}).json()
    ids = {o["obs_id"] for o in a["observations"]}
    assert set(re.findall(r"\[obs:([^\]]+)\]", a["text"])) <= ids


def test_okina_normalization():
    from app.agent.system1 import normalize
    assert normalize("Kāneʻohe") == "kaneohe"


def test_audit_chain():
    assert c.get("/api/audit/verify", headers={"x-kyd-role": "auditor"}).json()["ok"]
