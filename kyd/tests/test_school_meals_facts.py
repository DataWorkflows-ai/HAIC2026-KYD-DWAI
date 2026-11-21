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
    assert (hi["cep_participating_schools"], hi["cep_eligible_not_participating_schools"]) == (118, 74)
    assert (hi["cep_not_participating_enrolled"], hi["cep_not_participating_uncertified"]) == (45902, 22270)
    h4 = {o.indicator: o.value for o in repo().observations(["HD-04"])}
    h27 = {o.indicator: o.value for o in repo().observations(["HD-27"])}
    assert h4["public_school_enrolled"] == 1691 and h4["free_reduced_students"] == 1478
    assert h27["public_school_enrolled"] == 1890 and h27["free_reduced_students"] == 694
    assert all("charter" in o.method_note for o in repo().observations(["HD-14"], ["pct_free_reduced_meals"]))


def test_program_gaps_school_details_totals():
    j = TestClient(app).get("/api/districts/HI/program-gaps").json()
    cep = j["cep"]["eligible_not_participating"]
    assert cep["totals"] == {"schools": 74, "enrollment": 45902, "free_reduced": 23632, "uncertified": 22270}
    pahoa = [r for r in j["school_meals"]["rows"] if r["school_name"] == "Pahoa Elementary"][0]
    assert pahoa["house"] == "HD-04" and pahoa["senate"] == "SD-02"


def test_program_gaps_do_not_mix_state_and_district_ranges_or_unmatched_cep():
    c = TestClient(app)
    h24 = c.get("/api/districts/HD-24/program-gaps").json()
    act139 = next(r for r in h24["rows"] if r["program_id"] == "act139")
    assert act139["range_low"] is None and act139["range_high"]["value"] == 221
    tanf = next(r for r in h24["rows"] if r["program_id"] == "tanf")
    assert tanf["range_high"]["unit"] == "pct"
    med = next(r for r in h24["rows"] if r["program_id"] == "medquest")
    assert med["eligible"]["value"] == med["enrolled"]["value"] + med["gap"]["value"]
    assert all(r["house"] == "HD-24" for r in h24["cep"]["participating"]["rows"])
    h19 = c.get("/api/districts/HD-19/program-gaps").json()
    assert next(r for r in h19["rows"] if r["program_id"] == "snap")["gap"]["value"] == 607


def test_context_and_crosswalk_use_meals():
    j = TestClient(app).get("/api/districts/HD-14/program-context").json()
    assert j["school_meals"]["observations"] and "charter" in j["school_meals"]["note"]
    assert len(j["facts"]) >= 20 and all(f["program"] for f in j["facts"])
    sm = next(e for e in crosswalk.estimate("HD-14")["estimates"] if e["program_id"] == "school_meals")
    assert any(a.startswith("Actual:") for a in sm["assumptions"])
