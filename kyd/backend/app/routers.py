from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from . import audit
from .auth import Principal, current_principal
from .agent import tools
from .agent.orchestrator import ask
from .config import settings
from .models import AgentAnswer, AskRequest
from .services.graph import graph
from .services.repo import repo
from .services import breakdowns, crosswalk, program_context, rankings, representation as rep, uptake
from .services.cache import cached

api = APIRouter(prefix="/api")


Who = Depends(current_principal)


@api.get("/me")
def me(who: Principal = Who):
    return {"user": who.user, "role": who.role}


@api.get("/health")
def health():
    r = repo()
    return {"ok": True, "mode": settings().data_mode, "demo": r.demo, "llm": settings().llm_provider,
            "graph": graph().backend, "verification": _verification_summary(),
            "geographies": len(r.geographies()), "programs": len(graph().programs())}


@api.get("/geographies")
def geographies(geo_type: str | None = None):
    return repo().geographies(geo_type)


@api.get("/indicators")
def indicators():
    return repo().indicators()


@api.get("/districts/{geo_id}")
def district(geo_id: str, who: Principal = Who):
    try:
        p = tools.get_district_profile(geo_id)
    except KeyError:
        raise HTTPException(404, f"unknown geography {geo_id}")
    audit.record(who.user, who.role, "get_district_profile", geo_ids=[geo_id], row_count=len(p.observations))
    return p


@api.get("/compare")
def compare(a: str, b: str, who: Principal = Who):
    audit.record(who.user, who.role, "compare_district", geo_ids=[a, b])
    return tools.compare_district(a, b)


@api.get("/districts/{geo_id}/programs")
def district_programs(geo_id: str, who: Principal = Who):
    audit.record(who.user, who.role, "find_programs", geo_ids=[geo_id])
    return tools.find_programs(geo_id, limit=12)


@api.get("/districts/{geo_id}/cross-program")
def district_cross_program(geo_id: str, who: Principal = Who):
    try:
        out = crosswalk.estimate(geo_id)
    except KeyError:
        raise HTTPException(404, f"unknown geography {geo_id}")
    audit.record(who.user, who.role, "estimate_cross_program", geo_ids=[geo_id])
    return out


@api.get("/districts/{geo_id}/unemployment")
def district_unemployment(geo_id: str, dimension: str = "all", who: Principal = Who):
    try:
        out = breakdowns.unemployment(geo_id, dimension)
    except KeyError:
        raise HTTPException(404, f"unknown geography {geo_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    audit.record(who.user, who.role, "unemployment_breakdown", geo_ids=[geo_id])
    return out


@api.get("/districts/{geo_id}/program-context")
def district_program_context(geo_id: str, who: Principal = Who):
    try:
        out = program_context.context(geo_id)
    except KeyError:
        raise HTTPException(404, f"unknown geography {geo_id}")
    audit.record(who.user, who.role, "program_context", geo_ids=[geo_id])
    return out


@api.get("/rankings")
def district_rankings(geo_type: str = "sldl"):
    if geo_type not in ("sldl", "sldu"):
        raise HTTPException(400, "geo_type must be sldl (House) or sldu (Senate)")
    return rankings.rankings(geo_type)


@api.get("/map/{indicator}")
def map_layer(indicator: str, geo_type: str = "sldl"):
    return tools.get_map_layer(indicator, geo_type)


@api.get("/representation/{geo_id}")
def representation(geo_id: str):
    if not repo().geography(geo_id):
        raise HTTPException(404, f"unknown geography {geo_id}")
    return rep.representation(geo_id)


MAP_FIGURES = ["total_pop", "median_hh_income", "pct_below_fpl", "pct_65plus", "pct_uninsured", "pct_rent_burden_30"]


@api.get("/map-summary")
def map_summary(geo_type: str = "sldl"):
    """Everything a map popup needs for every district of a chamber, in a single request."""
    return _map_summary(geo_type)


@cached
def _map_summary(geo_type: str) -> dict:
    r = repo()
    geos = r.geographies(geo_type)
    obs = r.observations([g.geo_id for g in geos], MAP_FIGURES)
    by: dict[str, list] = {}
    for o in obs:
        by.setdefault(o.geo_id, []).append(o)
    order = {k: i for i, k in enumerate(MAP_FIGURES)}
    top = {}
    for g in geos:
        pm = tools.find_programs(g.geo_id, limit=1)
        top[g.geo_id] = pm[0].program.name if pm else None
    return {"roster": rep.roster_summary(), "overlap_method": rep.OVERLAP_METHOD, "local_method": rep.LOCAL_METHOD,
            "districts": [
        {"geo_id": g.geo_id, "name": g.name, "counties": g.counties, "member": rep.member(g.geo_id),
         "counterparts": rep.counterparts(g.geo_id), **rep.local_areas(g.geo_id), "top_program": top[g.geo_id],
         "figures": sorted(by.get(g.geo_id, []), key=lambda o: order[o.indicator])} for g in geos]}


@api.get("/districts/{geo_id}/context")
def district_context(geo_id: str):
    """Relationships for one district from the graph: overlaps, peers, neighborhoods, boards, council."""
    c = graph().district_context(geo_id)
    if not c:
        raise HTTPException(404, f"unknown district {geo_id}")
    return c


@api.get("/connections")
def connections(a: str, b: str):
    """How two districts are connected: overlap, peer, shared neighborhoods, boards, council, graph path."""
    return graph().connections(a, b)


def _verification_summary() -> dict | None:
    p = settings().data_dir / "verification_report.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text(encoding="utf-8"))
    return {"generated_at": r["generated_at"], "git_sha": r.get("git_sha"), **r["summary"]}


@api.get("/verification")
def verification(status: str | None = None):
    """Source verification report (kyd/verify/run.py) and which program capabilities it covers."""
    p = settings().data_dir / "verification_report.json"
    if not p.exists():
        raise HTTPException(404, "no verification report; run python kyd/verify/run.py")
    r = json.loads(p.read_text(encoding="utf-8"))
    checks = [c for c in r["checks"] if status is None or c["status"] == status]
    return {"summary": _verification_summary(), "sources": r["sources"], "capabilities": graph().capabilities(),
            "checks": checks}


@api.get("/programs")
def programs():
    return graph().programs()


@api.get("/programs/{program_id}/related")
def related(program_id: str):
    return graph().related(program_id)


@api.get("/sources")
def sources():
    return repo().sources()


@api.get("/districts/{geo_id}/uptake-peers")
def uptake_peers(geo_id: str, who: Principal = Depends(current_principal)):
    audit.record(who.user, who.role, "uptake_peers", geo_ids=[geo_id])
    return uptake.uptake_peers(geo_id)


@api.get("/finder-index")
@cached
def finder_index():
    """Everything the header search can jump to: districts, legislators, places, neighborhoods and ZIP codes.
    Places and ZIPs list each district they touch with its area share (slivers under 5% dropped)."""
    import csv
    out = [{"label": g.name, "kind": "district", "targets": [[g.geo_id, 1.0]], "keys": [g.geo_id.lower(), g.geo_id.replace("-", " ").lower()]}
           for g in repo().geographies() if g.geo_id[:2] in ("HD", "SD") or g.geo_id == "HI"]
    with (settings().data_dir / "legislators.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["name"]:
                role = "Senator" if r["geo_id"].startswith("SD") else "Representative"
                out.append({"label": f"{r['name']} ({role}, {r['geo_id']})", "kind": "legislator", "targets": [[r["geo_id"], 1.0]], "keys": []})
    p = settings().data_dir / "place_aliases.json"
    if p.exists():
        seen = set()
        for alias, a in json.loads(p.read_text(encoding="utf-8"))["aliases"].items():
            if a["name"] in seen:
                continue
            seen.add(a["name"])
            out.append({"label": a["name"], "kind": a.get("kind", "place"), "keys": [alias],
                        "targets": [[g, round(s, 3)] for g, s in (a.get("HD") or []) + (a.get("SD") or [])]})
    return out


@api.get("/source-library")
def source_library():
    """Every source the app draws on (kyd/data/sources.csv; SOURCES.md is generated from it)."""
    import csv
    path = settings().data_dir / "sources.csv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@api.get("/sources/observation/{obs_id}")
def cite(obs_id: str):
    o = repo().observation(obs_id)
    if not o:
        raise HTTPException(404, "unknown observation")
    src = next((s for s in repo().sources() if s.source_id == o.source_id), None)
    return {"observation": o, "source": src, "lineage": graph().lineage(o.indicator)}


@api.post("/agent/ask", response_model=AgentAnswer)
async def agent_ask(body: AskRequest, who: Principal = Who):
    a = await ask(body.question, body.geo_id)
    audit.record(who.user, who.role, "agent_ask", route=a.route, geo_ids=a.geo_ids,
                 row_count=len(a.observations), query=body.question)
    return a


@api.get("/audit/verify")
def audit_verify(who: Principal = Who):
    who.require("auditor", "admin")
    return audit.verify_chain()
