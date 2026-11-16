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
