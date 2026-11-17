"""Unemployment by demographic group (ACS 2020–2024): data, API, agent tool and number check."""
import asyncio

from fastapi.testclient import TestClient

from app.agent import system1, system2
from app.agent.orchestrator import ask
from app.agent.tools import TOOLS
from app.main import app
from app.services import breakdowns
from app.services.repo import repo

c = TestClient(app)


def test_overall_matches_acs_profile():
    for g in [f"HD-{i:02d}" for i in range(1, 52)] + [f"SD-{i:02d}" for i in range(1, 26)]:
        b = breakdowns.unemployment(g, "overall")["rows"]["overall"][0]["value"]
        p = repo().observations([g], ["unemployment_rate"])[0].value
        assert abs(b - p) <= 0.1, g


def test_api_shapes_and_flags():
    j = c.get("/api/districts/HD-44/unemployment").json()
    assert set(j["dimensions"]) == {"overall", "sex", "age_collapsed", "race_ethnicity", "education"}
    assert [r["label"] for r in j["rows"]["sex"]] == ["Male", "Female"]
    assert len(j["rows"]["age_collapsed"]) == 6 and j["county_geo_id"] == "CNTY-15003"
    assert any(r["flags"] == ["suppressed_cv"] for r in j["rows"]["race_ethnicity"])
    assert j["state"]["overall"][0]["value"] == 4.92
    assert "CNTY-15005" not in breakdowns._rows()                                   # Kalawao excluded
    assert c.get("/api/districts/HD-44/unemployment?dimension=bogus").status_code == 400


def test_agent_route_and_number_check():
    rt = system1.route("What is unemployment by race in HD 44?")
    assert rt.intent == "unemployment" and rt.geo_ids == ["HD-44"]
    a = asyncio.run(ask("What is unemployment by race in HD 44?", None))
    assert a.route == "S1" and "unreliable" in a.text
    out = TOOLS["unemployment_breakdown"]("HD-44", "sex")
    obs = system2.collect_obs(out)
    assert obs and not system2.unsupported_numbers("Male unemployment is 13.42% and female 5.24%.", obs)
    assert all(o["indicator"] == "unemployment_rate" for o in obs)


def test_s2_can_cite_unemployment_breakdowns(monkeypatch):
    """A comparison that escalates to System 2 and calls the unemployment tool must return 200 with
    those rows attached. They used to lack indicator, so building the answer raised ValidationError
    outside the System 2 fallback and the request 500ed."""
    out = TOOLS["unemployment_breakdown"]("HD-22", "sex")
    obs = system2.collect_obs({"result": out})

    async def fake(q, hint):
        return "Compare the two districts using the tool figures.", obs, [
            {"tool": "unemployment_breakdown", "args": {"geo_id": "HD-22", "dimension": "sex"}}]

    monkeypatch.setattr(system2, "run", fake)
    r = c.post("/api/agent/ask", json={"question": "Compare unemployment in House District 22 and House District 23"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["route"] == "S2"
    assert {o["obs_id"] for o in body["observations"]} == {row["obs_id"] for row in obs}
    assert all(o["indicator"] == "unemployment_rate" for o in body["observations"])


def test_partial_tool_figure_does_not_500(monkeypatch):
    async def fake(q, hint):
        return "No extra numbers.", [{"obs_id": "x", "value": 1.0}], []

    monkeypatch.setattr(system2, "run", fake)
    r = c.post("/api/agent/ask", json={"question": "Compare unemployment in House District 22 and House District 23"})
    assert r.status_code == 200, r.text
    assert r.json()["observations"] == []
