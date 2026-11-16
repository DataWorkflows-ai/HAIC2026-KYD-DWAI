"""Program indicators in kyd.sqlite (etl/load_programs.py) must equal what Crystal's analyses in
scripts/ compute, district by district, so the app and her scripts never disagree."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.agent.tools import find_programs
from app.main import app
from app.services.repo import repo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import ga_proxy, snap_gap, tanf_proxy  # noqa: E401,E402

CHAMBERS = (("house", "HD", 51), ("senate", "SD", 25))


def _vals(geo):
    return {o.indicator: o.value for o in repo().observations([geo])}


def test_program_indicators_match_crystal_scripts():
    for chamber, prefix, n in CHAMBERS:
        for d in range(1, n + 1):
            geo, v = f"{prefix}-{d:02d}", _vals(f"{prefix}-{d:02d}")
            s = snap_gap.get_snap_gap(chamber, d)
            assert v["pop_below_200fpl"] == s["eligible_proxy"]["count"], geo
            assert v["snap_hh_count"] == s["enrolled"]["count"], geo
            assert v["snap_persons_est"] == s["person_level"]["snap_persons_estimate"], geo
            assert v["snap_gap_persons"] == s["person_level"]["person_gap"], geo
            t = tanf_proxy.get_tanf_proxy(chamber, d)
            assert v["children_below_fpl"] == t["eligible_proxy"]["count"], geo
            assert v["pct_children_below_fpl"] == t["context"]["percent_of_related_children_below_poverty"], geo
            g = ga_proxy.get_ga_proxy(chamber, d, lenses=["poverty_18_64"])["poverty_18_64"]
            assert v["adults_18_64_below_fpl"] == g["count"], geo
            assert v["pct_adults_18_64_below_fpl"] == g["rate_percent"], geo


def test_state_values_and_sources():
    hi = _vals("HI")
    house = [_vals(f"HD-{d:02d}") for d in range(1, 52)]
    assert hi["snap_gap_persons"] == sum(h["snap_gap_persons"] for h in house)
    srcs = {s.source_id for s in repo().sources()}
    assert {"acs5_2024_s1701_sld", "acs5_2024_s2201_sld"} <= srcs
    for o in repo().observations(["HD-01", "SD-01", "HI"], ["pct_snap_gap", "children_below_fpl"]):
        assert o.source_id in srcs and o.vintage == "2020-2024"


def test_ranking_uses_program_data():
    ids = {m.program.program_id for g in ("SD-01", "HD-44") for m in find_programs(g, limit=20)}
    assert {"snap", "tanf", "ga", "aabd"} <= ids
    snap = next(m for m in find_programs("SD-01", limit=20) if m.program.program_id == "snap")
    assert snap.gap_note and "200% of poverty" in snap.gap_note


def test_program_indicators_on_map():
    r = TestClient(app).get("/api/map/pct_snap_gap", params={"geo_type": "sldl"})
    assert r.status_code == 200, r.text
    f = r.json()["features"]
    assert len(f) == 51 and all(x["value"] is not None for x in f)
