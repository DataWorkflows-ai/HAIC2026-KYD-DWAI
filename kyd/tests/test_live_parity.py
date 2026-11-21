"""Live mode (Postgres / Supabase) must answer exactly as the bundled SQLite does.

Runs only when KYD_TEST_PG=1 and KYD_DATABASE_URL points at a database loaded by etl/promote_to_postgres.py.
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

KYD = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.environ.get("KYD_TEST_PG") != "1", reason="set KYD_TEST_PG=1 with a loaded Postgres")


def _run(args, mode, **env):
    e = {**os.environ, "KYD_DATA_MODE": mode, "KYD_GRAPH_MODE": "fixture", "KYD_LLM_PROVIDER": "none", **env}
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=e, cwd=KYD / "backend")


def test_postgres_equals_repository():
    p = _run([str(KYD / "etl" / "promote_to_postgres.py"), "--check"], "sqlite")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "verified:" in p.stdout


def test_every_api_response_is_identical(tmp_path):
    out = {}
    for mode in ("sqlite", "live"):
        f = tmp_path / f"{mode}.json"
        p = _run([str(KYD / "verify" / "dump_api.py"), str(f)], mode)
        assert p.returncode == 0, p.stdout + p.stderr
        out[mode] = json.loads(f.read_text(encoding="utf-8"))
    a, b = out["sqlite"], out["live"]
    assert len(a) > 600 and set(a) == set(b)
    assert sum(v["status"] == 200 for v in a.values()) > 600
    different = [k for k in a if a[k] != b[k]]
    assert not different, f"{len(different)} responses differ, e.g. {different[:5]}"


def test_live_mode_reports_postgres_and_falls_back(tmp_path):
    c = sqlite3.connect(f"file:{KYD / 'data' / 'kyd.sqlite'}?mode=ro", uri=True)
    expected_observations = c.execute("SELECT count(*) FROM observation").fetchone()[0]
    c.close()
    code = ("import json,sys; sys.path.insert(0,'.'); from fastapi.testclient import TestClient; from app.main import app; "
            "h=TestClient(app).get('/api/health').json(); print(json.dumps(h))")
    h = json.loads(_run(["-c", code], "live").stdout.strip().splitlines()[-1])
    assert h["data_backend"] == "postgres" and h["files"] == "postgres" and h["fallback"] is None
    assert h["load_run"]["counts"]["observation"] == expected_observations and h["geographies"] == 77 and h["audit"]["store"] == "postgres"
    # database unreachable: runtime fails clearly by default; fallback is explicit only.
    failed = _run(["-c", code], "live", KYD_DATABASE_URL="postgresql://nobody@127.0.0.1:9/none",
                  KYD_PG_CONNECT_TIMEOUT="3")
    assert failed.returncode != 0 and "Connection" in (failed.stderr + failed.stdout)
    h = json.loads(_run(["-c", code], "live", KYD_DATABASE_URL="postgresql://nobody@127.0.0.1:9/none",
                        KYD_PG_CONNECT_TIMEOUT="3", KYD_LIVE_FALLBACK="true").stdout.strip().splitlines()[-1])
    assert h["data_backend"] == "sqlite" and h["files"] == "files" and h["fallback"] and h["geographies"] == 77


def test_live_mode_snap_gap_anchors_match_supabase_data():
    code = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from app.services.program_gaps import program_gaps; "
        "h24=program_gaps('HD-24'); hi=program_gaps('HI'); "
        "snap24=next(r for r in h24['rows'] if r['program_id']=='snap'); "
        "snaphi=next(r for r in hi['rows'] if r['program_id']=='snap'); "
        "print(json.dumps({'h24_gap': snap24['gap'].value, 'h24_moe': snap24['gap'].moe, "
        "'hi_eligible': snaphi['eligible'].value, 'hi_enrolled': snaphi['enrolled'].value, "
        "'hi_gap': snaphi['gap'].value, 'hi_reach': snaphi['reach'].value}))"
    )
    got = json.loads(_run(["-c", code], "live").stdout.strip().splitlines()[-1])
    assert got == {"h24_gap": 1755.0, "h24_moe": 268.0, "hi_eligible": 161104.0,
                   "hi_enrolled": 130188.0, "hi_gap": 30916.0, "hi_reach": 81.0}


def test_audit_chain_in_postgres():
    code = ("import sys; sys.path.insert(0,'.'); from app import audit; audit.record('t','viewer','parity_test',geo_ids=['HD-01']); "
            "audit.record('t','viewer','parity_test',query='call me at 808-555-0100'); v=audit.verify_chain(); print(v); "
            "assert v['ok'] and v['store']=='postgres' and v['entries']>=2 and not audit.status()['degraded']")
    p = _run(["-c", code], "live")
    assert p.returncode == 0, p.stdout + p.stderr
