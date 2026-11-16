"""Oʻahu crime ESTIMATE by district: reconciles with the research file; labelled; Oʻahu only."""
import csv
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.repo import repo

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "hpd_crime"
c = TestClient(app)


def test_house_sum_matches_research_file():
    rows = [r for r in csv.DictReader((RAW / "crime_by_legislative_district_ESTIMATE.csv").open())
            if r["layer"] == "house" and r["year"] == "2025" and r["offense"] == "total"
            and r["weight"] == "pop_share_or_area_if_pop_lt50"]
    src = sum(float(r["estimated_count"]) for r in rows)
    app_sum = sum(o.value for o in repo().observations([f"HD-{i:02d}" for i in range(1, 52)], ["crime_total_est"]))
    assert len(rows) == 34 and abs(app_sum - src) <= 34          # per-district rounding only
    assert repo().observations(["CNTY-15003"], ["crime_total_est"])[0].value == 15096   # HPD Table 1


def test_labelled_estimate_and_oahu_only():
    o = repo().observations(["HD-25"], ["crime_rate_per_1k_est"])[0]
    assert "ESTIMATE" in o.method_note and "traced" in o.method_note
    assert not repo().observations(["HD-01"], ["crime_total_est"])        # Hawaiʻi Island: no HPD data
    j = c.get("/api/districts/HD-25/program-context").json()["crime"]
    assert "ESTIMATE" in j["title"] and len(j["trend"]) == 9 and j["oahu_median_per_1k"] > 0
    assert c.get("/api/districts/HD-01/program-context").json()["crime"] is None
