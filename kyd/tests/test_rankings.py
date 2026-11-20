"""District rankings: complete, correctly ordered, cited, estimates labelled."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.repo import repo

c = TestClient(app)


def test_house_and_senate_rankings():
    for t, n in (("sldl", 51), ("sldu", 25)):
        j = c.get("/api/rankings", params={"geo_type": t}).json()
        assert len(j["rows"]) == n
        cols = {x["indicator"]: x for x in j["columns"]}
        assert cols["pct_below_fpl"]["kind"] == "survey" and cols["pct_snap_gap"]["kind"] == "estimate"
        for ind in ("pct_below_fpl", "pct_snap_gap"):
            cells = sorted((r["cells"][ind] for r in j["rows"]), key=lambda x: x["rank"])
            assert [x["rank"] for x in cells] == list(range(1, n + 1))
            vals = [x["obs"]["value"] for x in cells]
            assert vals == sorted(vals, reverse=True)
            assert all(repo().observation(x["obs"]["obs_id"]) for x in cells)     # every cell citable
    assert c.get("/api/rankings", params={"geo_type": "county"}).status_code == 400


def test_snap_gap_shown_as_range():
    j = c.get("/api/rankings").json()
    col = next(x for x in j["columns"] if x["indicator"] == "pct_snap_gap")
    assert col["alt_indicator"] == "pct_snap_gap_low"
    assert j["state_alt"]["pct_snap_gap"]["value"] == 9.8
    for r in j["rows"]:
        alt = r["cells"]["pct_snap_gap"]["alt"]
        assert alt["indicator"] == "pct_snap_gap_low" and repo().observation(alt["obs_id"])


def test_crime_only_oahu():
    j = c.get("/api/rankings").json()
    ranked = [r for r in j["rows"] if r["cells"]["crime_violent_per_1k_est"]]
    assert len(ranked) == 34 and all(r["geo_id"] >= "HD-18" for r in ranked)
