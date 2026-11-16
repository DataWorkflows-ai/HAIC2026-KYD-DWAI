"""Agent tools (§2.2). These are the only functions that return figures, and every
figure they return is an Observation that carries its citation."""
from __future__ import annotations
import math
from ..models import DistrictProfile, Observation, ProgramMatch
from ..services.graph import graph
from ..services.cache import cached
from ..services.repo import repo
from ..services.quality import significantly_different

CORE = ["total_pop", "median_age", "households", "median_hh_income", "per_capita_income", "pct_below_fpl",
        "pct_child_poverty", "pct_65plus_poverty", "pct_snap_hh", "pct_ssi_hh", "pct_cash_assist_hh",
        "pct_under5", "pct_under18", "pct_65plus", "pct_renter", "pct_rent_burden_30", "median_gross_rent",
        "median_home_value", "pct_no_vehicle", "pct_uninsured", "pct_disability", "pct_veterans",
        "pct_foreign_born", "pct_limited_english", "pct_bachelors_plus", "pct_broadband", "unemployment_rate"]
# Non-ACS indicators shown on the district profile after the ACS core set
PROFILE_EXTRA = ["pct_pop_lidac", "pct_pop_lidac_most", "pct_sba_ela_proficient", "pct_sba_math_proficient",
                 "pct_hsa_science_proficient"]
# Program-analysis indicators (etl/load_programs.py, from Crystal's scripts/ analyses)
PROGRAM_IND = ["pct_below_200fpl", "pct_snap_gap", "snap_gap_persons", "pop_below_200fpl", "snap_hh_count",
               "snap_persons_est", "pct_children_below_fpl", "children_below_fpl", "pct_adults_18_64_below_fpl",
               "adults_18_64_below_fpl", "laus_unemp_rate", "laus_labor_force"]
PEER_FEATURES = ["median_hh_income", "pct_below_fpl", "pct_65plus", "pct_under18", "pct_renter",
                 "pct_rent_burden_30", "pct_uninsured", "unemployment_rate", "pct_limited_english"]


def _by_ind(obs: list[Observation]) -> dict[str, Observation]:
    return {o.indicator: o for o in obs}


def get_district_profile(geo_id: str, indicators: list[str] | None = None) -> DistrictProfile:
    r = repo()
    g = r.geography(geo_id)
    if not g:
        raise KeyError(geo_id)
    inds = indicators or CORE + PROFILE_EXTRA
    order = {k: i for i, k in enumerate(inds)}
    obs = sorted(r.observations([geo_id], inds), key=lambda o: order.get(o.indicator, 99))
    acs = [o for o in obs if o.source_id.startswith("acs")]
    comps = {"state": r.observations(["HI"], inds)}
    if g.counties:
        comps["county"] = r.observations([g.counties[0]], inds)
    return DistrictProfile(geography=g, observations=obs, comparisons=comps,
                           peers=peer_districts(geo_id), data_as_of=max((o.vintage for o in acs or obs), default=""))


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


@cached
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


@cached
def chamber_medians(geo_id: str) -> dict[str, float]:
    """Median across districts of the same chamber; the reference when no state value exists."""
    r = repo()
    g = r.geography(geo_id)
    if not g or g.geo_type not in ("sldu", "sldl"):
        return {}
    ids = [x.geo_id for x in r.geographies(g.geo_type)]
    vals: dict[str, list[float]] = {}
    for o in r.observations(ids, CORE):
        if o.value is not None:
            vals.setdefault(o.indicator, []).append(o.value)
    return {k: sorted(v)[len(v) // 2] for k, v in vals.items()}


def find_programs(geo_id: str, limit: int = 6) -> list[ProgramMatch]:
    """Rank programs by relevance × gap. The score is transparent and the rationale is returned (§2.5)."""
    return list(_rank_programs(geo_id)[:limit])


@cached
def _rank_programs(geo_id: str) -> tuple[ProgramMatch, ...]:
    r, gr = repo(), graph()
    obs = _by_ind(r.observations([geo_id], CORE + PROGRAM_IND))
    state = _by_ind(r.observations(["HI"], CORE + PROGRAM_IND))
    base = chamber_medians(geo_id)
    out = []
    for p in gr.programs():
        # pct_snap_hh is an uptake measure, not a need measure. It feeds the gap term only.
        need = [obs[i] for i in p.proxy_indicators if i in obs and i != "pct_snap_hh"]
        if not need:
            continue
        ratios, why = [], []
        for o in need:
            s = state.get(o.indicator)
            ref, ref_name = (s.value, "state") if s and s.value else (base.get(o.indicator), "median district")
            if o.value is None or not ref:
                continue
            ratio = o.value / ref
            # higher than reference = more need, except income (inverse)
            ratio = 1 / ratio if o.unit == "usd" else ratio
            ratios.append(ratio)
            why.append(f"{o.label}: {o.value:g} vs {ref_name} {ref:g}"
                       + (" (low reliability)" if "suppressed_cv" in o.flags else ""))
        if not ratios:
            continue
        score = sum(ratios) / len(ratios)
        gap = None
        if p.program_id == "snap":
            g, gs = obs.get("pct_snap_gap"), state.get("pct_snap_gap")
            e, u = obs.get("pct_below_fpl"), obs.get("pct_snap_hh")
            if g and g.value is not None and gs and gs.value is not None:
                gap = (f"Estimated {g.value:g}% of people below 200% of poverty are not in SNAP households "
                       f"(state {gs.value:g}%). Counts-based proxy: SNAP households x average household size "
                       f"vs people below 200% FPL; eligibility also depends on assets and household makeup.")
                score *= 1 + max(0, (g.value - gs.value) / 100)
            elif e and u and e.value and u.value is not None:
                gap = (f"Uptake proxy: {u.value:g}% of households get SNAP; {e.value:g}% of people are below "
                       f"the poverty level. Different universes (households vs people), so this signals a "
                       f"possible gap only. SNAP's gross income limit is above the poverty line.")
                score *= 1 + max(0, (e.value - u.value) / 100)
        out.append(ProgramMatch(program=p, score=round(score, 3), eligible_proxy=need[0],
                                uptake_proxy=obs.get("pct_snap_hh") if p.program_id == "snap" else None,
                                gap_note=gap, rationale=why))
    return tuple(sorted(out, key=lambda m: m.score, reverse=True))


def estimate_eligible(geo_id: str, program_id: str) -> dict:
    """Population-level proxy only. This is never an eligibility determination (§9.3)."""
    p = graph().program(program_id)
    if not p:
        raise KeyError(program_id)
    obs = repo().observations([geo_id], p.proxy_indicators + ["total_pop"])
    return {"program": p, "observations": obs,
            "note": "Informational population estimate. The administering agency determines eligibility."}


def estimate_cross_program(geo_id: str) -> dict:
    """Likely-eligible counts for other programs, from SNAP participation and income ladders (services/crosswalk.py)."""
    from ..services.crosswalk import estimate
    return estimate(geo_id)


def unemployment_breakdown(geo_id: str, dimension: str = "all") -> dict:
    """Unemployment rate by sex, age, race/ethnicity or education (ACS 2020–2024), with county and state rows."""
    from ..services.breakdowns import unemployment
    return unemployment(geo_id, dimension)


def get_map_layer(indicator: str, geo_type: str = "sldl") -> dict:
    r = repo()
    ids = [g.geo_id for g in r.geographies(geo_type)]
    return {"indicator": indicator, "geo_type": geo_type, "features": r.observations(ids, [indicator])}


def export_summary(geo_id: str) -> dict:
    prof = get_district_profile(geo_id)
    return {"profile": prof, "programs": find_programs(geo_id), "format": "pdf-pending"}


def district_connections(a: str, b: str | None = None) -> dict:
    """Relationships from the graph, worded without numbers so S2's figure check stays strict:
    one district's context, or how two districts connect."""
    def cover(s: float) -> str:
        return "all" if s >= 0.95 else "most" if s >= 0.5 else "part"
    gr = graph()
    if b:
        c = gr.connections(a, b)
        if "error" in c:
            raise KeyError(c["error"])
        return {**{k: v for k, v in c.items() if k != "overlap"},
                "overlap": None if c["overlap"] is None else f"{cover(c['overlap'])} of {a} lies in {b}"}
    c = gr.district_context(a)
    if not c:
        raise KeyError(a)
    return {"geo_id": a, "name": c["name"], "county": c["county"], "peers_by_profile": c["peers"],
            "neighborhoods": c["neighborhoods"],
            "overlapping_districts": [f"{x['geo_id']} ({cover(x['share_of_this'])})" for x in c["counterparts"]],
            "neighborhood_boards": [f"No. {x['number']} {x['name']} ({cover(x['share'])})" for x in c["boards"]],
            "council_districts": [f"{x['body']} {x['name'] if x['number'] is None else 'District ' + str(x['number'])} "
                                  f"({cover(x['share'])})" for x in c["council"]]}


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
    {"name": "estimate_cross_program",
     "description": "From SNAP participation and income-to-poverty counts, estimate how many households or people in "
                    "a district likely meet the eligibility rules of other programs (free school meals, Lifeline, "
                    "LIHEAP, WIC, Med-QUEST income test). Each estimate has its rule, citation, range and confidence.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}}, "required": ["geo_id"]}},
    {"name": "unemployment_breakdown",
     "description": "Unemployment rate (%, with 90% MOE) for a district by sex, age group, race/ethnicity or "
                    "education (ages 25-64), with the district's county and the state for comparison. ACS 2020-2024. "
                    "Rows flagged suppressed_cv are unreliable; say so if you use them.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"},
                    "dimension": {"type": "string", "enum": ["all", "overall", "sex", "age_collapsed",
                                                             "race_ethnicity", "education"]}},
                    "required": ["geo_id"]}},
    {"name": "district_connections",
     "description": "Relationships from the knowledge graph. With only `a`: the district's county, neighborhoods, "
                    "overlapping House/Senate districts, neighborhood boards, council districts and most similar peer "
                    "districts. With `a` and `b`: how the two districts connect (overlap, peers, shared neighborhoods, "
                    "boards, council, shortest graph path). Contains no statistics.",
     "parameters": {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                    "required": ["a"]}},
]
TOOLS = {"get_district_profile": get_district_profile, "compare_district": compare_district,
         "find_programs": find_programs, "estimate_eligible": estimate_eligible,
         "get_map_layer": get_map_layer, "export_summary": export_summary,
         "district_connections": district_connections, "estimate_cross_program": estimate_cross_program,
         "unemployment_breakdown": unemployment_breakdown}
