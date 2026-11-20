"""Live mode (Postgres / Supabase) must answer exactly as the bundled SQLite does.

Runs only when KYD_TEST_PG=1 and KYD_DATABASE_URL points at a database loaded by etl/promote_to_postgres.py.
"""
import json
import os
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
    code = ("import json,sys; sys.path.insert(0,'.'); from fastapi.testclient import TestClient; from app.main import app; "
            "h=TestClient(app).get('/api/health').json(); print(json.dumps(h))")
    h = json.loads(_run(["-c", code], "live").stdout.strip().splitlines()[-1])
    assert h["data_backend"] == "postgres" and h["files"] == "postgres" and h["fallback"] is None
    assert h["load_run"]["counts"]["observation"] == 10253 and h["geographies"] == 77 and h["audit"]["store"] == "postgres"
    # database unreachable: the app still starts, serves the bundled copy, and says so
    h = json.loads(_run(["-c", code], "live", KYD_DATABASE_URL="postgresql://nobody@127.0.0.1:9/none",
                        KYD_PG_CONNECT_TIMEOUT="3").stdout.strip().splitlines()[-1])
    assert h["data_backend"] == "sqlite" and h["files"] == "files" and h["fallback"] and h["geographies"] == 77


def test_audit_chain_in_postgres():
    code = ("import sys; sys.path.insert(0,'.'); from app import audit; audit.record('t','viewer','parity_test',geo_ids=['HD-01']); "
            "audit.record('t','viewer','parity_test',query='call me at 808-555-0100'); v=audit.verify_chain(); print(v); "
            "assert v['ok'] and v['store']=='postgres' and v['entries']>=2 and not audit.status()['degraded']")
    p = _run(["-c", code], "live")
    assert p.returncode == 0, p.stdout + p.stderr
