"""LIDAC share of residents by district (2020 block-group population)."""
import csv
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.repo import repo

ROOT = Path(__file__).resolve().parents[2]
c = TestClient(app)


def _v(g, k):
    o = repo().observations([g], [k])
    return o[0].value if o else None


def test_state_share_matches_direct_blockgroup_sum():
    flags = {r["bg_geoid"]: int(r["unified_lidac"]) for r in csv.DictReader((ROOT / "data/raw/gis/lidac_bg_flags.csv").open())}
    pop = {r["bg"]: 0.0 for r in csv.DictReader((ROOT / "kyd/data/bg_district_crosswalk.csv").open())}
    for r in csv.DictReader((ROOT / "kyd/data/bg_district_crosswalk.csv").open()):
        if r["chamber"] == "house":
            pop[r["bg"]] += float(r["pop20_allocated"])
    tot, lid = sum(pop.values()), sum(p for b, p in pop.items() if flags[b] >= 1)
    assert abs(_v("HI", "pct_pop_lidac") - 100 * lid / tot) < 0.1
    assert len(flags) == 1056 and set(flags) == set(pop)


def test_districts_bounded_and_ordered():
    for g in [f"HD-{i:02d}" for i in range(1, 52)] + [f"SD-{i:02d}" for i in range(1, 26)]:
        a, m = _v(g, "pct_pop_lidac"), _v(g, "pct_pop_lidac_most")
        assert 0 <= m <= a <= 100, g


def test_on_profile_and_map():
    p = c.get("/api/districts/HD-03").json()
    assert "pct_pop_lidac" in {o["indicator"] for o in p["observations"]}
    assert p["data_as_of"] == "2020-2024"
    m = c.get("/api/map/pct_pop_lidac", params={"geo_type": "sldl"}).json()
    assert len(m["features"]) == 51
