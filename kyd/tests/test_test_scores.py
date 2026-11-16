"""HIDOE 2025 test scores rolled up by school location (charters excluded)."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "kyd.sqlite"


def _q(sql, *a):
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def test_every_district_has_scores():
    for pre, n in (("HD", 51), ("SD", 25)):
        got = _q("SELECT COUNT(DISTINCT geo_id) FROM observation WHERE indicator='pct_sba_ela_proficient' AND geo_id LIKE ?", pre + "%")
        assert got[0][0] == n


def test_house_districts_sum_to_state():
    hd = _q("SELECT SUM(value) FROM observation WHERE indicator='sba_tested' AND geo_id LIKE 'HD%'")[0][0]
    sd = _q("SELECT SUM(value) FROM observation WHERE indicator='sba_tested' AND geo_id LIKE 'SD%'")[0][0]
    hi = _q("SELECT value FROM observation WHERE indicator='sba_tested' AND geo_id='HI'")[0][0]
    assert abs(hd - hi) <= 51 and abs(sd - hi) <= 25
    # HIDOE statewide ELA tested is 82,269 including charters; non-charter schools are most of it
    assert 70_000 < hi < 82_269


def test_rates_are_percentages():
    for (v,) in _q("SELECT value FROM observation WHERE indicator LIKE 'pct_%proficient'"):
        assert 0 < v < 100


def test_program_context_has_test_scores():
    # HD-44 is on Oʻahu, where the crime block also runs (guards a name clash that once emptied this card)
    from fastapi.testclient import TestClient
    from app.main import app
    t = TestClient(app).get("/api/districts/HD-44/program-context").json()["test_scores"]
    assert {o["indicator"] for o in t["observations"]} >= {"pct_sba_ela_proficient", "pct_sba_math_proficient"}
    assert t["state"]["pct_sba_ela_proficient"]
