"""Births and deaths by district (ESTIMATE from Hawaiʻi-IBIS)."""
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

DB = Path(__file__).resolve().parents[1] / "data" / "kyd.sqlite"


def _q(sql, *a):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def test_house_sum_matches_dbedt_2024_within_one_percent():
    b = _q("SELECT SUM(value) FROM observation WHERE indicator='births_est_2024' AND geo_id LIKE 'HD%'")[0][0]
    d = _q("SELECT SUM(value) FROM observation WHERE indicator='deaths_est_2024' AND geo_id LIKE 'HD%'")[0][0]
    assert abs(b - 14_883) / 14_883 < 0.01 and abs(d - 12_489) / 12_489 < 0.01   # DBEDT Data Book 2025, Table 2.01


def test_every_district_has_estimates_labelled():
    for pre, n in (("HD", 51), ("SD", 25)):
        assert _q("SELECT COUNT(DISTINCT geo_id) FROM observation WHERE indicator='births_avg_est' AND geo_id LIKE ?", pre + "%")[0][0] == n
    assert all("ESTIMATE" in note for (note,) in _q("SELECT method_note FROM observation WHERE indicator='deaths_avg_est'"))


def test_program_context_vital_block():
    v = TestClient(app).get("/api/districts/HD-44/program-context").json()["vital"]
    assert {o["indicator"] for o in v["observations"]} >= {"births_avg_est", "death_rate_per_1k_est"}
    assert len(v["trend"]) == 25 and v["state"]["birth_rate_per_1k_est"]
