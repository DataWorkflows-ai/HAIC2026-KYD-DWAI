"""SNAP uptake peers (similar need, smaller reach gap)."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.uptake import uptake_peers


def test_peers_have_similar_need_and_smaller_gap():
    d = uptake_peers("SD-12")
    need, gap = d["need"].value, d["gap"].value
    assert d["peers"]
    for p in d["peers"]:
        assert abs(p["need"].value - need) <= max(3.0, 0.15 * need)
        assert p["gap"].value <= gap - 2
        assert p["more_reached"]["value"] == round(d["people_below_200fpl"].value * (gap - p["gap"].value) / 100)
    assert [p["gap"].value for p in d["peers"]] == sorted(p["gap"].value for p in d["peers"])


def test_endpoint_and_non_district():
    c = TestClient(app)
    assert c.get("/api/districts/HD-28/uptake-peers").json()["peers"]
    assert c.get("/api/districts/HI/uptake-peers").json()["peers"] == []
