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
            assert v["tanf_deep_poverty_children"] == t["eligible_proxy"]["count"], geo
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
    assert snap.gap_note and "poverty households" in snap.gap_note


def test_snap_gap_benchmark_end():
    hi = _vals("HI")
    assert (hi["snap_eligible_usda"], hi["snap_participants_usda"]) == (161_104, 130_188)
    assert (hi["snap_participation_rate"], hi["snap_participation_rate_ci_low"],
            hi["snap_participation_rate_ci_high"], hi["snap_participation_rate_us"]) == (81, 73, 88, 88)
    assert hi["snap_gap_low_persons"] == 161_104 - 130_188
    for _, prefix, n in CHAMBERS:
        ds = [_vals(f"{prefix}-{d:02d}") for d in range(1, n + 1)]
        assert abs(sum(v["snap_gap_low_persons"] for v in ds) - hi["snap_gap_low_persons"]) <= n / 2
        for v in ds:
            assert v["pct_snap_gap_low"] == round(100 * v["snap_gap_low_persons"] / v["pop_below_200fpl"], 1)


def test_verified_program_gap_anchors():
    hi = _vals("HI")
    h24 = _vals("HD-24")
    assert hi["snap_strict_gap_households"] == 31_739
    assert h24["snap_strict_gap_households"] == 1_755
    assert h24["tanf_deep_poverty_children"] >= 0
    assert hi["tanf_deep_poverty_children"] == 18_183
    assert (hi["tanf_reach_low"], hi["tanf_reach_high"]) == (18.7, 24.0)
    assert hi["act139_acs_upper_children"] == 36_492
    assert hi["wic_eligible_est"] == 44_888
    assert hi["wic_participating_est"] == 25_804
    assert hi["medquest_uninsured_eligible"] == 13_544


def test_snap_gap_range():
    for geo in ("HI", "HD-28", "SD-13", "HD-36"):
        rng = next(m for m in find_programs(geo, limit=20) if m.program.program_id == "snap").gap_range
        assert rng and rng.low.persons.value <= rng.high.persons.value, geo
        if geo == "HI":
            assert {rng.low.basis, rng.high.basis} == {"USDA range low", "USDA range high"}, geo
        else:
            assert rng.low.basis == rng.high.basis == "ACS strict district cell", geo
        assert {o.indicator for o in rng.benchmark} >= {"snap_participation_rate", "snap_participation_rate_us"}
    hd36 = next(m for m in find_programs("HD-36", limit=20) if m.program.program_id == "snap").gap_range
    assert hd36.low.basis == "ACS strict district cell" and hd36.high.grade == "B"
    assert "HD-36" in hd36.note and "House 24" not in hd36.note


def test_snap_included_even_when_not_top_ranked():
    for geo in ("HD-18", "HD-33", "HD-37", "HD-39", "HD-40", "HD-41", "SD-16", "SD-20", "SD-25"):
        assert any(m.program.program_id == "snap" and m.gap_range for m in find_programs(geo, limit=12)), geo


def test_program_indicators_on_map():
    r = TestClient(app).get("/api/map/pct_snap_gap", params={"geo_type": "sldl"})
    assert r.status_code == 200, r.text
    f = r.json()["features"]
    assert len(f) == 51 and all(x["value"] is not None for x in f)
