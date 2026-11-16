"""School-meals district figures and statewide program facts."""
import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services import crosswalk
from app.services.repo import repo

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "research"


def test_meals_match_research_rollup():
    rows = list(csv.DictReader((RAW / "team2a_school_meals_fr_by_house_district_SY2025-26_no_charter.csv").open()))
    for r in rows:
        g = f"HD-{int(float(r['house_2022'])):02d}"
        v = {o.indicator: o.value for o in repo().observations([g])}
        assert v["free_reduced_students"] == float(r["free_reduced"]) and v["public_school_enrolled"] == float(r["enrolled"])
        assert abs(v["pct_free_reduced_meals"] - float(r["pct_free_reduced"])) < 0.02, g
    hi = {o.indicator: o.value for o in repo().observations(["HI"])}
    assert hi["public_school_enrolled"] == 153435 and hi["free_reduced_students"] == 78927
    assert all("charter" in o.method_note for o in repo().observations(["HD-14"], ["pct_free_reduced_meals"]))


def test_context_and_crosswalk_use_meals():
    j = TestClient(app).get("/api/districts/HD-14/program-context").json()
    assert j["school_meals"]["observations"] and "charter" in j["school_meals"]["note"]
    assert len(j["facts"]) >= 20 and all(f["program"] for f in j["facts"])
    sm = next(e for e in crosswalk.estimate("HD-14")["estimates"] if e["program_id"] == "school_meals")
    assert any(a.startswith("Actual:") for a in sm["assumptions"])
