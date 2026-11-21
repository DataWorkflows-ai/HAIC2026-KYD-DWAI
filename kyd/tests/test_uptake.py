"""SNAP uptake peers (strict ACS poverty-household reach)."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.uptake import uptake_peers


def test_peers_have_similar_need_and_smaller_gap():
    d = uptake_peers("SD-12")
    need, reach = d["need"].value, d["gap"].value
    assert d["peers"]
    for p in d["peers"]:
        assert abs(p["need"].value - need) <= max(100.0, 0.25 * need)
        assert p["gap"].value >= reach + 2
        assert p["more_reached"]["value"] == round(need * (p["gap"].value - reach) / 100)
        assert "households" in p["more_reached"]["label"].lower()
        assert not (p["gap"].moe and p["gap"].value and p["gap"].moe / p["gap"].value > 0.30)
    assert [p["gap"].value for p in d["peers"]] == sorted((p["gap"].value for p in d["peers"]), reverse=True)


def test_endpoint_and_non_district():
    c = TestClient(app)
    assert c.get("/api/districts/HD-24/uptake-peers").json()["peers"]
    assert c.get("/api/districts/HI/uptake-peers").json()["peers"] == []
