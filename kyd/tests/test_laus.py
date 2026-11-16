"""DBEDT LAUS unemployment: district roll-up, county totals, trend."""
from fastapi.testclient import TestClient

from app.main import app
from app.services.repo import repo

COUNTIES = ["CNTY-15001", "CNTY-15003", "CNTY-15007", "CNTY-15009"]


def _v(geo, ind):
    o = repo().observations([geo], [ind])
    return o[0].value if o else None


def test_district_labor_force_adds_to_state():
    for prefix, n in (("HD", 51), ("SD", 25)):
        lf = sum(_v(f"{prefix}-{i:02d}", "laus_labor_force") for i in range(1, n + 1))
        assert abs(lf - _v("HI", "laus_labor_force")) / _v("HI", "laus_labor_force") < 0.001, prefix
    assert _v("HI", "laus_labor_force") == sum(_v(c, "laus_labor_force") for c in COUNTIES)


def test_rates_are_plausible_and_trend_complete():
    for i in range(1, 52):
        assert 0 < _v(f"HD-{i:02d}", "laus_unemp_rate") < 20
    assert _v("HI", "laus_unemp_rate_2020") > 10 and _v("HI", "laus_unemp_rate") < 4      # pandemic peak vs 2025
    j = TestClient(app).get("/api/districts/HD-44/program-context").json()["employment"]
    assert len(j["trend"]) == 12 and all(t["county"] and t["state"] for t in j["trend"])
    assert {o["indicator"] for o in j["district"]} >= {"laus_unemp_rate", "unemployment_rate"}


def test_trend_indicators_hidden_from_map_list():
    inds = {i["indicator"]: i for i in TestClient(app).get("/api/indicators").json()}
    assert inds["laus_unemp_rate_2020"]["topic"] == "employment_trend" and inds["laus_unemp_rate"]["unit"] == "pct"
