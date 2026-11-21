"""Cross-program estimates and island/statewide program context."""
import asyncio

from fastapi.testclient import TestClient

from app.agent import system1
from app.agent.orchestrator import ask
from app.main import app
from app.services import crosswalk
from app.services.repo import repo

c = TestClient(app)
DISTRICTS = [f"HD-{i:02d}" for i in range(1, 52)] + [f"SD-{i:02d}" for i in range(1, 26)]


def test_estimates_follow_their_inputs():
    for g in DISTRICTS:
        v = {o.indicator: o.value for o in repo().observations([g])}
        est = {e["program_id"]: e for e in crosswalk.estimate(g)["estimates"]}
        assert set(est) == {"school_meals", "lifeline", "liheap", "wic", "med_quest"}, g
        assert est["school_meals"]["estimate"] == round(v["snap_hh_children"]), g
        assert est["lifeline"]["estimate"] == round(v["snap_hh_count"]), g
        lo, hi = est["liheap"]["low"], est["liheap"]["high"]
        assert lo <= hi <= v["households"] + 1, g
        m = est["med_quest"]
        assert v["pop_below_125fpl"] <= m["estimate"] <= v["pop_below_150fpl"], g
        assert est["wic"]["low"] <= est["wic"]["high"], g
        for e in est.values():
            assert e["source"]["url"].startswith("https://") and e["confidence"] in ("high", "medium", "low")
            assert all(repo().observation(i) for i in e["input_obs_ids"]), (g, e["program_id"])


def test_poverty_ladder_is_monotonic():
    for g in DISTRICTS + ["HI"]:
        v = {o.indicator: o.value for o in repo().observations([g])}
        ladder = [v[k] for k in ("pop_below_125fpl", "pop_below_138fpl", "pop_below_150fpl", "pop_below_185fpl",
                                 "pop_below_200fpl")]
        assert ladder == sorted(ladder), g


def test_cross_program_api_and_agent():
    r = c.get("/api/districts/SD-01/cross-program")
    assert r.status_code == 200 and len(r.json()["estimates"]) == 5
    assert c.get("/api/districts/XX-99/cross-program").status_code == 404
    rt = system1.route("How many SNAP households in SD 1 also qualify for other programs?")
    assert rt.intent == "cross_program" and rt.geo_ids == ["SD-01"]
    a = asyncio.run(ask("How many SNAP households in SD 1 also qualify for other programs?", None))
    assert a.route == "S1" and a.intent == "cross_program" and "Lifeline" in a.text and a.observations


def test_common_words_are_not_places():
    assert system1.route("Who in HD 19 is automatically eligible for school meals?").geo_ids == ["HD-19"]


def test_state_context_uses_statewide_figures():
    j = c.get("/api/districts/HI/program-context").json()
    assert j["county"] == "Statewide"
    meals = {o["indicator"]: o["value"] for o in j["school_meals"]["observations"]}
    assert meals["free_reduced_students"] == 78927 and meals["public_school_enrolled"] == 153435
    assert j["school_meals"]["state_pct"] is None
    rate = next(o for o in j["employment"]["state"] if o["indicator"] == "laus_unemp_rate")
    assert rate["value"] == 2.4 and len(j["employment"]["trend"]) == 12
    assert j["employment"]["trend"][-1]["state"] == 2.4 and j["employment"]["trend"][6]["state"] > 10
    assert j["medquest"]["statewide"] > 0 and len(j["medquest"]["islands"]) >= 4 and j["medquest"]["trend"]
    assert j["tanf_island"]["tanf_persons"] > 0 and len(j["tanf_island"]["islands"]) == 4
    assert j["county_snap"]["rows"] and j["hpha"]["units"] > 0 and j["hud"]["observations"]
    assert j["test_scores"]["observations"] and j["vital"]["trend"]
    assert j["crime"] is None
    gaps = c.get("/api/districts/HI/program-gaps").json()
    snap = next(r for r in gaps["rows"] if r["program_id"] == "snap")
    assert snap["gap"]["value"] == 30916 and snap["eligible"]["value"] == 161104
    assert snap["unit"] == "people"


def test_program_context():
    for g, county, n_islands in (("HD-13", "Maui", 3), ("SD-01", "Hawaii", 1), ("HD-19", "Oahu", 1)):
        j = c.get(f"/api/districts/{g}/program-context").json()
        assert j["county"] == county
        assert len(j["medquest"]["islands"]) == n_islands and j["medquest"]["statewide"] > 0
        assert j["tanf_island"]["tanf_persons"] > 0 and j["county_snap"]["rows"]
        assert j["tanf_underenrollment"]["available"] and j["tanf_underenrollment"]["groups"]
