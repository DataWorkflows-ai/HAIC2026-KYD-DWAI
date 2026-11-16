"""Official ACS state and county profile values fill the County and State comparison columns."""
from fastapi.testclient import TestClient

from app.main import app


def test_profile_has_county_and_state_for_core_rates():
    j = TestClient(app).get("/api/districts/HD-44").json()
    st = {o["indicator"]: o["value"] for o in j["comparisons"]["state"]}
    co = {o["indicator"]: o["value"] for o in j["comparisons"]["county"]}
    for k in ("median_hh_income", "pct_below_fpl", "pct_child_poverty", "unemployment_rate", "pct_uninsured"):
        assert st.get(k) is not None and co.get(k) is not None, k
    assert 90_000 < st["median_hh_income"] < 110_000 and 5 < st["pct_below_fpl"] < 15


def test_every_county_has_values():
    from app.services.repo import repo
    for g in ("CNTY-15001", "CNTY-15003", "CNTY-15007", "CNTY-15009"):
        assert {o.indicator for o in repo().observations([g], ["median_hh_income", "pct_below_fpl"])} == {"median_hh_income", "pct_below_fpl"}
