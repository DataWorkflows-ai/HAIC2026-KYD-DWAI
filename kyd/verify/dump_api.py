"""Write every read-only API response to one JSON file, so two data modes can be compared.

    KYD_DATA_MODE=sqlite python kyd/verify/dump_api.py a.json
    KYD_DATA_MODE=live   python kyd/verify/dump_api.py b.json      # then: the two files must be identical

Covers every GET route that takes no parameter, a district id, an indicator, a program id or an observation id,
for all 77 geographies. Skips the routes that describe the process itself (/health, /me, /audit/verify).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

SKIP = {"/api/health", "/api/me", "/api/audit/verify"}


def dump() -> dict:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import api
    from app.services.repo import repo
    c = TestClient(app)
    r = repo()
    geos = [g.geo_id for g in r.geographies()]
    inds = [i["indicator"] for i in r.indicators()]
    progs = [p["program_id"] for p in c.get("/api/programs").json()]
    obs = [o.obs_id for g in geos[:6] for o in r.observations([g])[:40]]
    fill = {"geo_id": geos, "indicator": inds, "program_id": progs, "obs_id": obs}
    out: dict[str, object] = {}
    for route in api.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or "GET" not in getattr(route, "methods", ()) or path in SKIP:
            continue
        params = [p.strip("{}") for p in path.split("/") if p.startswith("{")]
        if len(params) > 1 or any(p not in fill for p in params):
            continue
        urls = [path] if not params else [path.replace("{" + params[0] + "}", v) for v in fill[params[0]]]
        for u in urls:
            resp = c.get(u)
            out[u] = {"status": resp.status_code, "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text}
    a, b = geos[1], geos[2]
    for u in (f"/api/compare?a={a}&b={b}", f"/api/connections?a={a}&b={b}", "/api/rankings?geo_type=sldl",
              "/api/rankings?geo_type=sldu", "/api/geographies?geo_type=sldu"):
        resp = c.get(u)
        out[u] = {"status": resp.status_code, "body": resp.json()}
    for q, g in (("How many people are below poverty in House District 44?", None), ("Which programs fit this district?", "HD-24"),
                 ("Compare this district with HD-36 on SNAP", "HD-24"), ("What is unemployment by age here?", "SD-07")):
        resp = c.post("/api/agent/ask", json={"question": q, "geo_id": g})
        out[f"ask:{q}|{g}"] = {"status": resp.status_code, "body": resp.json()}
    return out


if __name__ == "__main__":
    d = dump()
    Path(sys.argv[1]).write_text(json.dumps(d, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print(f"{len(d)} responses, {sum(1 for v in d.values() if v['status'] == 200)} with status 200")
