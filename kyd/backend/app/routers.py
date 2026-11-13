from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from . import audit
from .agent import tools
from .agent.orchestrator import ask
from .config import settings
from .models import AgentAnswer, AskRequest
from .services.graph import graph
from .services.repo import repo

api = APIRouter(prefix="/api")


def _who(req: Request) -> tuple[str, str]:
    # SSO later. For now, trust a reverse-proxy header, defaulting to anonymous.
    return req.headers.get("x-kyd-user", "anonymous"), req.headers.get("x-kyd-role", "viewer")


@api.get("/health")
def health():
    r = repo()
    return {"ok": True, "mode": settings().data_mode, "demo": r.demo, "llm": settings().llm_provider,
            "geographies": len(r.geographies()), "programs": len(graph().programs())}


@api.get("/geographies")
def geographies(geo_type: str | None = None):
    return repo().geographies(geo_type)


@api.get("/indicators")
def indicators():
    return repo().indicators()


@api.get("/districts/{geo_id}")
def district(geo_id: str, req: Request):
    try:
        p = tools.get_district_profile(geo_id)
    except KeyError:
        raise HTTPException(404, f"unknown geography {geo_id}")
    audit.record(*_who(req), "get_district_profile", geo_ids=[geo_id], row_count=len(p.observations))
    return p


@api.get("/compare")
def compare(a: str, b: str, req: Request):
    audit.record(*_who(req), "compare_district", geo_ids=[a, b])
    return tools.compare_district(a, b)


@api.get("/districts/{geo_id}/programs")
def district_programs(geo_id: str, req: Request):
    audit.record(*_who(req), "find_programs", geo_ids=[geo_id])
    return tools.find_programs(geo_id, limit=12)


@api.get("/map/{indicator}")
def map_layer(indicator: str, geo_type: str = "sldl"):
    return tools.get_map_layer(indicator, geo_type)


@api.get("/programs")
def programs():
    return graph().programs()


@api.get("/programs/{program_id}/related")
def related(program_id: str):
    return graph().related(program_id)


@api.get("/sources")
def sources():
    return repo().sources()


@api.get("/sources/observation/{obs_id}")
def cite(obs_id: str):
    o = repo().observation(obs_id)
    if not o:
        raise HTTPException(404, "unknown observation")
    src = next((s for s in repo().sources() if s.source_id == o.source_id), None)
    return {"observation": o, "source": src, "lineage": graph().lineage(o.indicator)}


@api.post("/agent/ask", response_model=AgentAnswer)
async def agent_ask(body: AskRequest, req: Request):
    a = await ask(body.question, body.geo_id)
    audit.record(*_who(req), "agent_ask", route=a.route, geo_ids=a.geo_ids,
                 row_count=len(a.observations), query=body.question)
    return a


@api.get("/audit/verify")
def audit_verify(req: Request):
    if _who(req)[1] not in ("auditor", "admin"):
        raise HTTPException(403, "auditor role required")
    return audit.verify_chain()
