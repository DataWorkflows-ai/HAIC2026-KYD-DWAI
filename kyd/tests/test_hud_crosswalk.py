"""Tract → district crosswalk and HUD subsidized-housing indicators."""
import csv
from collections import defaultdict
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.repo import repo

DATA = Path(__file__).resolve().parents[1] / "data"
HUD = Path(__file__).resolve().parents[2] / "data" / "raw" / "hud" / "hi_tract_hud_2025.csv"


def test_crosswalk_weights_sum_to_one():
    rows = list(csv.DictReader((DATA / "tract_district_crosswalk.csv").open()))
    for ch, n in (("house", 51), ("senate", 25)):
        s = defaultdict(float)
        for r in rows:
            if r["chamber"] == ch:
                s[r["tract"]] += float(r["weight"])
        assert len(s) == 435 and all(abs(v - 1) < 0.002 for v in s.values()), ch
        assert len({r["geo_id"] for r in rows if r["chamber"] == ch}) == n


def test_hud_totals_reconcile_with_source():
    src = [r for r in csv.DictReader(HUD.open()) if r["program_label"] == "Summary of All HUD Programs"]
    total = sum(max(float(r["total_units"]), 0) for r in src)
    unplaced = sum(max(float(r["total_units"]), 0) for r in src if r["code"].endswith("999999"))
    hi = {o.indicator: o.value for o in repo().observations(["HI"])}
    assert hi["hud_units_total"] == round(total)
    for prefix, n in (("HD", 51), ("SD", 25)):
        d = sum(o.value for o in repo().observations([f"{prefix}-{i:02d}" for i in range(1, n + 1)], ["hud_units_total"]))
        assert abs(d - (total - unplaced)) <= n, prefix     # per-district rounding only


def test_hud_in_program_context():
    j = TestClient(app).get("/api/districts/HD-29/program-context").json()
    ids = [o["indicator"] for o in j["hud"]["observations"]]
    assert "hud_units_total" in ids and "hud_units_hcv" in ids and j["hud"]["state_per_1k_hh"] > 0
