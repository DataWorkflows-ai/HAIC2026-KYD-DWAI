"""Run from backend/: pytest ../tests"""
import re
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/api/health").json()["ok"]


def test_every_figure_has_citation():
    p = c.get("/api/districts/HD-22").json()
    for o in p["observations"]:
        assert o["obs_id"] and o["source_id"] and o["vintage"]
        assert c.get(f"/api/sources/observation/{o['obs_id']}").status_code == 200


def test_guardrails_refuse():
    for q in ["Who in HD 5 receives SNAP?", "Which candidate should win SD 9?"]:
        assert c.post("/api/agent/ask", json={"question": q}).json()["route"] == "REFUSED"


def test_s1_numbers_are_cited():
    a = c.post("/api/agent/ask", json={"question": "Profile of House District 22"}).json()
    ids = {o["obs_id"] for o in a["observations"]}
    assert set(re.findall(r"\[obs:([^\]]+)\]", a["text"])) <= ids


def test_okina_normalization():
    from app.agent.system1 import normalize
    assert normalize("Kāneʻohe") == "kaneohe"


def test_audit_chain():
    from app.auth import mint
    from app.config import settings
    s = settings()
    old, s.auth_secret = s.auth_secret, "test-secret"
    try:
        tok = mint("auditor.test", "auditor")
        assert c.get("/api/audit/verify", headers={"Authorization": f"Bearer {tok}"}).json()["ok"]
    finally:
        s.auth_secret = old


# ── real data, map and representation ──────────────────────────────────────
import csv
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_real_data_mode_is_default():
    h = c.get("/api/health").json()
    assert h["mode"] == "sqlite" and not h["demo"] and h["geographies"] == 77


def test_acs_matches_teammate_database():
    """Cross-check the KYD loader against data/districts.db (built independently by scripts/process_acs.py)."""
    db = sqlite3.connect(REPO / "data" / "districts.db")
    pairs = {"median_hh_income": "median_hh_income_estimate", "pct_below_fpl": "pct_people_poverty_percent",
             "pct_uninsured": "pct_no_health_insurance_percent", "pct_snap_hh": "snap_benefits_percent"}
    for chamber, table, prefix in (("house", "house_districts", "HD"), ("senate", "senate_districts", "SD")):
        for row in db.execute(f"SELECT district, {', '.join(pairs.values())} FROM {table}"):
            p = c.get(f"/api/districts/{prefix}-{row[0]:02d}").json()
            got = {o["indicator"]: o["value"] for o in p["observations"]}
            for (k, _), raw in zip(pairs.items(), row[1:]):
                want = float(str(raw).replace(",", "").replace("%", ""))
                assert got[k] == want, (prefix, row[0], k, got[k], want)


def test_every_district_has_overlap_and_seat():
    for gid in [f"HD-{i:02d}" for i in range(1, 52)] + [f"SD-{i:02d}" for i in range(1, 26)]:
        r = c.get(f"/api/representation/{gid}").json()
        assert r["counterparts"], gid
        assert r["member"] is not None, gid
        assert abs(sum(x["share_of_this"] for x in r["counterparts"]) - 1) < 0.03, gid


def test_roster_has_no_party_and_cites_sources():
    rows = list(csv.DictReader((REPO / "kyd" / "data" / "legislators.csv").open(encoding="utf-8")))
    assert len(rows) == 76 and "party" not in rows[0]
    for r in rows:
        assert r["status"] in ("official", "secondary", "verify", "pending")
        assert r["status"] == "pending" or (r["name"] and r["source_url"]), r["geo_id"]


def test_map_summary_shape():
    d = c.get("/api/map-summary?geo_type=sldl").json()
    assert len(d["districts"]) == 51
    assert all(x["figures"] and x["counterparts"] for x in d["districts"])


def test_health_names_the_frontend_build_being_served():
    """/api/health reports which built frontend is live, so a deploy can be checked without opening the page."""
    served = re.search(r"assets/(index-[\w-]+\.js)", c.get("/").text).group(1)
    assert c.get("/api/health").json()["frontend"] == served
