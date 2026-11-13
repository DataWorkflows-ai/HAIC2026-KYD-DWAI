"""Agent tools (§2.2). These are the only functions that return figures, and every
figure they return is an Observation that carries its citation."""
from __future__ import annotations
import math
from ..models import DistrictProfile, Observation, ProgramMatch
from ..services.graph import graph
from ..services.repo import repo
from ..services.quality import significantly_different

CORE = ["total_pop", "median_age", "median_hh_income", "pct_below_fpl", "pct_below_200fpl", "pct_snap_hh",
        "pct_under18", "pct_65plus", "pct_rent_burden_30", "pct_uninsured", "pct_disability",
        "pct_veterans", "pct_limited_english", "unemployment_rate"]
PEER_FEATURES = ["median_hh_income", "pct_below_200fpl", "pct_65plus", "pct_under18",
                 "pct_rent_burden_30", "pct_uninsured", "unemployment_rate"]


def _by_ind(obs: list[Observation]) -> dict[str, Observation]:
    return {o.indicator: o for o in obs}


def get_district_profile(geo_id: str, indicators: list[str] | None = None) -> DistrictProfile:
    r = repo()
    g = r.geography(geo_id)
    if not g:
        raise KeyError(geo_id)
    inds = indicators or CORE
    obs = r.observations([geo_id], inds)
    comps = {"state": r.observations(["HI"], inds)}
    if g.counties:
        comps["county"] = r.observations([g.counties[0]], inds)
    return DistrictProfile(geography=g, observations=obs, comparisons=comps,
                           peers=peer_districts(geo_id), data_as_of=max((o.vintage for o in obs), default=""))


def compare_district(a: str, b: str, indicators: list[str] | None = None) -> dict:
    r = repo()
    inds = indicators or CORE
    A, B = _by_ind(r.observations([a], inds)), _by_ind(r.observations([b], inds))
    rows = []
    for k in inds:
        if k in A and k in B:
            rows.append({"indicator": k, "a": A[k], "b": B[k],
                         "significant": significantly_different(A[k], B[k])})
    return {"a": a, "b": b, "rows": rows}


def peer_districts(geo_id: str, k: int = 4) -> list[str]:
    """kNN on standardized features among districts of the same chamber (§4.1–4.2)."""
    r = repo()
    g = r.geography(geo_id)
    if not g or g.geo_type not in ("sldu", "sldl"):
        return []
    ids = [x.geo_id for x in r.geographies(g.geo_type)]
    obs = r.observations(ids, PEER_FEATURES)
    mat: dict[str, dict[str, float]] = {}
    for o in obs:
        if o.value is not None:
            mat.setdefault(o.geo_id, {})[o.indicator] = o.value
    stats = {}
    for f in PEER_FEATURES:
        vals = [m[f] for m in mat.values() if f in m]
        mu = sum(vals) / len(vals)
        sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 or 1
        stats[f] = (mu, sd)
    z = {gid: [(m.get(f, stats[f][0]) - stats[f][0]) / stats[f][1] for f in PEER_FEATURES] for gid, m in mat.items()}
    me = z.get(geo_id)
    if me is None:
        return []
    d = sorted((math.dist(me, v), gid) for gid, v in z.items() if gid != geo_id)
    return [gid for _, gid in d[:k]]


def find_programs(geo_id: str, limit: int = 6) -> list[ProgramMatch]:
    """Rank programs by relevance × gap. The score is transparent and the rationale is returned (§2.5)."""
    r, gr = repo(), graph()
    obs = _by_ind(r.observations([geo_id], CORE))
    state = _by_ind(r.observations(["HI"], CORE))
    out = []
    for p in gr.programs():
        # pct_snap_hh is an uptake measure, not a need measure. It feeds the gap term only.
        need = [obs[i] for i in p.proxy_indicators if i in obs and i != "pct_snap_hh"]
        if not need:
            continue
        ratios, why = [], []
        for o in need:
            s = state.get(o.indicator)
            if o.value is None or not s or not s.value:
                continue
            ratio = o.value / s.value
            # higher than state = more need, except income (inverse)
            ratio = 1 / ratio if o.indicator == "median_hh_income" else ratio
            ratios.append(ratio)
            why.append(f"{o.label}: {o.value:g} vs state {s.value:g}"
                       + (" (low reliability)" if "suppressed_cv" in o.flags else ""))
        if not ratios:
            continue
        score = sum(ratios) / len(ratios)
        gap = None
        if p.program_id == "snap" and "pct_below_200fpl" in obs and "pct_snap_hh" in obs:
            e, u = obs["pct_below_200fpl"], obs["pct_snap_hh"]
            if e.value and u.value is not None:
                gap = (f"Uptake proxy: {u.value:g}% of households get SNAP, while {e.value:g}% of people are "
                       f"below 200% FPL. These are different universes, so this indicates potential gap only.")
                score *= 1 + max(0, (e.value - u.value) / 100)
        out.append(ProgramMatch(program=p, score=round(score, 3), eligible_proxy=need[0],
                                uptake_proxy=obs.get("pct_snap_hh") if p.program_id == "snap" else None,
                                gap_note=gap, rationale=why))
    return sorted(out, key=lambda m: m.score, reverse=True)[:limit]


def estimate_eligible(geo_id: str, program_id: str) -> dict:
    """Population-level proxy only. This is never an eligibility determination (§9.3)."""
    p = graph().program(program_id)
    if not p:
        raise KeyError(program_id)
    obs = repo().observations([geo_id], p.proxy_indicators + ["total_pop"])
    return {"program": p, "observations": obs,
            "note": "Informational population estimate. The administering agency determines eligibility."}


def get_map_layer(indicator: str, geo_type: str = "sldl") -> dict:
    r = repo()
    ids = [g.geo_id for g in r.geographies(geo_type)]
    return {"indicator": indicator, "geo_type": geo_type, "features": r.observations(ids, [indicator])}


def export_summary(geo_id: str) -> dict:
    prof = get_district_profile(geo_id)
    return {"profile": prof, "programs": find_programs(geo_id), "format": "pdf-pending"}


TOOL_SPECS = [  # JSON-schema descriptions handed to System 2
    {"name": "get_district_profile", "description": "Core indicators for one district, with county and state comparisons.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"},
                    "indicators": {"type": "array", "items": {"type": "string"}}}, "required": ["geo_id"]}},
    {"name": "compare_district", "description": "Compare two geographies, with a significance test per indicator.",
     "parameters": {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                    "required": ["a", "b"]}},
    {"name": "find_programs", "description": "Rank assistance programs by need and potential gap for a district.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}}, "required": ["geo_id"]}},
    {"name": "estimate_eligible", "description": "Population proxy for a program in a district.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}, "program_id": {"type": "string"}},
                    "required": ["geo_id", "program_id"]}},
]
TOOLS = {"get_district_profile": get_district_profile, "compare_district": compare_district,
         "find_programs": find_programs, "estimate_eligible": estimate_eligible,
         "get_map_layer": get_map_layer, "export_summary": export_summary}
