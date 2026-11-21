"""Agent tools (§2.2). These are the only functions that return figures, and every
figure they return is an Observation that carries its citation."""
from __future__ import annotations
import math
from ..models import DistrictProfile, GapRange, Observation, ProgramMatch, RangeEnd
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
                 "pct_hsa_science_proficient", "births_avg_est", "deaths_avg_est", "birth_rate_per_1k_est",
                 "death_rate_per_1k_est"]
# Program-analysis indicators (etl/load_programs.py, from Crystal's scripts/ analyses)
PROGRAM_IND = ["pct_below_200fpl", "pct_snap_gap", "snap_gap_persons", "pop_below_200fpl", "snap_hh_count",
               "snap_persons_est", "snap_poverty_hh_total", "snap_poverty_hh_receiving",
               "snap_strict_gap_households", "snap_poverty_hh_reach_rate", "tanf_deep_poverty_children",
               "pct_children_below_fpl", "children_below_fpl", "pct_adults_18_64_below_fpl",
               "adults_18_64_below_fpl", "laus_unemp_rate", "laus_labor_force", "snap_gap_low_persons", "pct_snap_gap_low"]
SNAP_BENCHMARKS = ["snap_participation_rate", "snap_participation_rate_ci_low", "snap_participation_rate_ci_high",
                   "snap_participation_rate_us", "snap_eligible_usda", "snap_participants_usda"]
PEER_FEATURES = ["median_hh_income", "pct_below_fpl", "pct_65plus", "pct_under18", "pct_renter",
                 "pct_rent_burden_30", "pct_uninsured", "unemployment_rate", "pct_limited_english"]


def _by_ind(obs: list[Observation]) -> dict[str, Observation]:
    return {o.indicator: o for o in obs}


COUNTY_GEO = {"Hawaiʻi County": "CNTY-15001", "City & County of Honolulu": "CNTY-15003",
              "Kauaʻi County": "CNTY-15007", "Maui County": "CNTY-15009"}


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
    if g.counties and COUNTY_GEO.get(g.counties[0]):
        comps["county"] = r.observations([COUNTY_GEO[g.counties[0]]], inds)
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
    ranked = list(_rank_programs(geo_id))
    shown = ranked[:limit]
    if geo_id.startswith(("HD", "SD")) and not any(m.program.program_id == "snap" for m in shown):
        snap = next((m for m in ranked if m.program.program_id == "snap"), None)
        if snap:
            shown = (shown[:-1] if len(shown) >= limit else shown) + [snap]
    return shown


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
        gap, rng = None, None
        if p.program_id == "snap":
            g, gs = obs.get("snap_strict_gap_households"), state.get("snap_strict_gap_households")
            e, u = obs.get("pct_below_fpl"), obs.get("pct_snap_hh")
            rng = snap_gap_range(geo_id)
            if g and g.value is not None and gs and gs.value is not None:
                if rng:
                    gap = (f"{g.value:,.0f} poverty households do not report SNAP in ACS 2020-2024 "
                           f"(90% MOE ±{g.moe:,.0f} where available). USDA's statewide federal-rules gap is "
                           f"about 31,000 eligible people, range about 15,000-46,000.")
                else:
                    gap = f"{g.value:,.0f} poverty households do not report SNAP in ACS 2020-2024."
                score *= 1 + max(0, (g.value / max(gs.value, 1)) - 1) / 10
            elif e and u and e.value and u.value is not None:
                gap = (f"Uptake proxy: {u.value:g}% of households get SNAP; {e.value:g}% of people are below "
                       f"the poverty level. Different universes (households vs people), so this signals a "
                       f"possible gap only. SNAP's gross income limit is above the poverty line.")
                score *= 1 + max(0, (e.value - u.value) / 100)
        out.append(ProgramMatch(program=p, score=round(score, 3), eligible_proxy=need[0],
                                uptake_proxy=obs.get("pct_snap_hh") if p.program_id == "snap" else None,
                                gap_note=gap, gap_range=rng, rationale=why))
    return tuple(sorted(out, key=lambda m: m.score, reverse=True))


@cached
def snap_gap_range(geo_id: str) -> GapRange | None:
    """SNAP gap display. Districts use ACS B22003 poverty-household cells; the state uses USDA's official people gap."""
    r = repo()
    keys = ["snap_strict_gap_households", "snap_poverty_hh_reach_rate", "snap_gap_low_persons",
            "snap_gap_usda_low", "snap_gap_usda_high"]
    o = _by_ind(r.observations([geo_id], keys))
    if geo_id == "HI":
        if "snap_gap_low_persons" not in o:
            return None
        main = RangeEnd(persons=o["snap_gap_low_persons"], share=None, grade="B", basis="USDA official",
                        method="USDA FY2022 eligible people minus eligible participants")
        low = RangeEnd(persons=o["snap_gap_usda_low"], share=None, grade="B", basis="USDA range low",
                       method="Rounded lower end using USDA rate interval and eligible SE")
        high = RangeEnd(persons=o["snap_gap_usda_high"], share=None, grade="B", basis="USDA range high",
                        method="Rounded upper end using USDA rate interval and eligible SE")
        return GapRange(low=low, high=high, benchmark=r.observations(["HI"], SNAP_BENCHMARKS), note=f"Point estimate: {main.persons.value:,.0f}.",
                        is_not="Not a district ranking and not a Hawaiʻi BBCE eligible count; USDA uses federal rules.")
    if "snap_strict_gap_households" not in o:
        return None
    end = RangeEnd(persons=o["snap_strict_gap_households"], share=o.get("snap_poverty_hh_reach_rate"), grade="B",
                   basis="ACS strict district cell",
                   method="Poverty households not reporting SNAP (B22003_E006), ACS 2020-2024")
    return GapRange(low=end, high=end, benchmark=r.observations(["HI"], SNAP_BENCHMARKS),
                    note=f"District figure is poverty households, not people. {geo_id} is "
                         f"{end.persons.value:,.0f}"
                         + (f" ±{end.persons.moe:,.0f}" if end.persons.moe else "")
                         + " households.",
                    is_not="Not a count of individuals and not an eligibility decision. ACS under-reports SNAP; agency rules decide eligibility.")


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


def uptake_peers(geo_id: str) -> dict:
    """Districts with similar need (share below 200% of poverty) that reach more of it with SNAP (services/uptake.py)."""
    from ..services.uptake import uptake_peers as f
    return f(geo_id)


def program_gaps(geo_id: str) -> dict:
    """Demo-ready program gaps for SNAP, WIC, Med-QUEST, TANF, meals/CEP, Act 139 and utilities."""
    from ..services.program_gaps import program_gaps as f
    return f(geo_id)


CHAMBER_GEO = {"house": "sldl", "senate": "sldu", "county": "county"}


def rank_districts(indicator: str, chamber: str = "house", n: int = 5, order: str = "highest") -> dict:
    """Top (or bottom) districts for one indicator. Survey values carry a 90% MOE; neighbours whose intervals
    overlap are not reliably different, so the ties are reported."""
    r = repo()
    if indicator not in {i["indicator"] for i in r.indicators()}:
        raise KeyError(f"unknown indicator {indicator}")
    ids = [g.geo_id for g in r.geographies(CHAMBER_GEO[chamber])]
    obs = sorted((o for o in r.observations(ids, [indicator]) if o.value is not None),
                 key=lambda o: o.value, reverse=order == "highest")
    top = obs[:max(1, min(n, 10))]
    def ci(o):
        m = o.moe or 0
        return o.value - m, o.value + m
    ties = [f"{a.geo_id} and {b.geo_id}" for a, b in zip(top, top[1:])
            if a.moe and b.moe and ci(a)[0] <= ci(b)[1] and ci(b)[0] <= ci(a)[1]]
    return {"indicator": indicator, "chamber": chamber, "order": order, "of": len(obs), "ranked": top,
            "state": r.observations(["HI"], [indicator]),
            "not_reliably_different": ties}


def get_map_layer(indicator: str, geo_type: str = "sldl") -> dict:
    r = repo()
    ids = [g.geo_id for g in r.geographies(geo_type)]
    return {"indicator": indicator, "geo_type": geo_type, "features": r.observations(ids, [indicator])}


def export_summary(geo_id: str) -> dict:
    prof = get_district_profile(geo_id)
    return {"profile": prof, "programs": find_programs(geo_id), "program_gaps": program_gaps(geo_id),
            "format": "pdf-pending"}


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
    {"name": "uptake_peers",
     "description": "SNAP uptake peers: districts in the same chamber with similar need (share of residents below 200% "
                    "of poverty) whose SNAP reach gap is smaller, and an estimate of how many more people this district "
                    "would reach at each peer's rate. All values are estimates from ACS counts, not enrollment records.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}}, "required": ["geo_id"]}},
    {"name": "district_connections",
     "description": "Relationships from the knowledge graph. With only `a`: the district's county, neighborhoods, "
                    "overlapping House/Senate districts, neighborhood boards, council districts and most similar peer "
                    "districts. With `a` and `b`: how the two districts connect (overlap, peers, shared neighborhoods, "
                    "boards, council, shortest graph path). Contains no statistics.",
     "parameters": {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                    "required": ["a"]}},
    {"name": "snap_gap_range",
     "description": "The SNAP gap for one geography. Districts return ACS poverty households not reporting SNAP "
                    "(with reach among poverty households); statewide returns USDA people and range. `is_not` says what it is not.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}}, "required": ["geo_id"]}},
    {"name": "program_gaps",
     "description": "Show program gaps for one district or statewide, with eligible/enrolled/gap/reach where public data supports it, "
                    "school/CEP drilldowns, official links, sources, caveats, and informational-only labels.",
     "parameters": {"type": "object", "properties": {"geo_id": {"type": "string"}}, "required": ["geo_id"]}},
    {"name": "rank_districts",
     "description": "Districts ranked by one indicator (highest or lowest first), with the state value. "
                    "`not_reliably_different` lists neighbouring pairs whose 90% margins overlap; mention them.",
     "parameters": {"type": "object", "properties": {"indicator": {"type": "string"},
                    "chamber": {"type": "string", "enum": ["house", "senate", "county"]},
                    "n": {"type": "integer", "minimum": 1, "maximum": 10},
                    "order": {"type": "string", "enum": ["highest", "lowest"]}}, "required": ["indicator"]}},
]
TOOLS = {"get_district_profile": get_district_profile, "compare_district": compare_district,
         "find_programs": find_programs, "estimate_eligible": estimate_eligible,
         "get_map_layer": get_map_layer, "export_summary": export_summary,
         "district_connections": district_connections, "estimate_cross_program": estimate_cross_program,
         "unemployment_breakdown": unemployment_breakdown, "uptake_peers": uptake_peers,
         "rank_districts": rank_districts, "snap_gap_range": snap_gap_range, "program_gaps": program_gaps}
