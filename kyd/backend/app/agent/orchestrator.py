"""Entry point for /api/agent/ask. Runs System 1 → optional System 2, then validation."""
from __future__ import annotations
import logging
from ..models import AgentAnswer, Observation, ProgramMatch
from ..services.repo import repo
from . import system1, system2
from .tools import compare_district, find_programs, get_district_profile

log = logging.getLogger("kyd.agent")
HEADLINE = ["total_pop", "median_hh_income", "pct_below_fpl", "pct_65plus", "pct_rent_burden_30", "pct_uninsured"]


def _fmt(o: Observation) -> str:
    if o.value is None:
        return "n/a"
    v = f"${o.value:,.0f}" if o.unit == "usd" else f"{o.value:g}%" if o.unit == "pct" else f"{o.value:,.0f}" \
        if o.unit == "count" else f"{o.value:g}"
    caveat = " (uncertain estimate)" if "suppressed_cv" in o.flags else ""
    return f"{v} ±{o.moe:g}{caveat} [obs:{o.obs_id}]" if o.moe else f"{v}{caveat} [obs:{o.obs_id}]"


def _anchor_unreliable(obs: list[Observation]) -> bool:
    return any("suppressed_cv" in o.flags for o in obs if o.indicator in HEADLINE)


def answer_s1(rt: system1.Route) -> AgentAnswer:
    name = lambda g: (repo().geography(g).name if repo().geography(g) else g)
    trace = [{"tool": rt.intent, "args": {"geo_ids": rt.geo_ids}}]
    if rt.intent == "compare":
        c = compare_district(*rt.geo_ids[:2])
        lines = [f"- {r['a'].label}: {_fmt(r['a'])} vs {_fmt(r['b'])}"
                 + ("" if r["significant"] else " (difference not statistically significant)") for r in c["rows"]
                 if r["a"].indicator in HEADLINE]
        obs = [r[k] for r in c["rows"] for k in ("a", "b")]
        return AgentAnswer(text=f"{name(rt.geo_ids[0])} compared with {name(rt.geo_ids[1])}:\n" + "\n".join(lines),
                           route="S1", intent="compare", geo_ids=rt.geo_ids, observations=obs, trace=trace)
    g = rt.geo_ids[0]
    if rt.intent == "programs":
        pm: list[ProgramMatch] = find_programs(g)
        lines = [f"{i+1}. {m.program.name}: {'; '.join(m.rationale[:2])}" for i, m in enumerate(pm)]
        obs = [m.eligible_proxy for m in pm if m.eligible_proxy]
        return AgentAnswer(text=f"Programs most relevant to {name(g)}, ranked by indicated need relative to the state:\n"
                           + "\n".join(lines) + "\n\nEligibility is determined by each administering agency.",
                           route="S1", intent="programs", geo_ids=[g], observations=obs, programs=pm, trace=trace)
    p = get_district_profile(g)
    lines = [f"- {o.label}: {_fmt(o)}" for o in p.observations if o.indicator in HEADLINE]
    return AgentAnswer(text=f"{p.geography.name} at a glance (ACS {p.data_as_of}):\n" + "\n".join(lines),
                       route="S1", intent="profile", geo_ids=[g], observations=p.observations, trace=trace)


def _district_label(geo_id: str) -> str:
    return f"{'Senate' if geo_id.startswith('SD') else 'House'} District {int(geo_id[3:])}"


def _clarify_place(rt: system1.Route, reasons: list[str]) -> AgentAnswer | None:
    """A place that spans several districts, and no LLM to reason about it: ask which district."""
    split = [p for p in rt.places if not p["dominant"] and p["candidates"]]
    if not split:
        return None
    p = split[0]
    opts = [_district_label(g) for g in p["candidates"]]
    listed = opts[0] if len(opts) == 1 else ", ".join(opts[:-1]) + f" or {opts[-1]}"
    return AgentAnswer(text=f"{p['name']} falls in more than one district. Do you mean {listed}?",
                       route="S1", intent=rt.intent, geo_ids=p["candidates"], escalation_reasons=reasons)


def _fallback(rt: system1.Route, reason: str) -> AgentAnswer:
    """S2 is unavailable or failed. Answer with a template if the route allows it, otherwise ask."""
    reasons = rt.reasons + [reason]
    if (c := _clarify_place(rt, reasons)) is not None:
        return c
    if rt.geo_ids and len(rt.geo_ids) <= 2:
        if rt.intent not in ("compare", "programs") or (rt.intent == "compare" and len(rt.geo_ids) < 2):
            rt.intent = "profile"                                 # unclear intent, one district → its profile
        a = answer_s1(rt)
        a.escalation_reasons = reasons
        return a
    return AgentAnswer(text="Which district do you mean? For example, “House District 22” or “Senate District 9”.",
                       route="S1", intent=rt.intent, escalation_reasons=reasons)


async def ask(question: str, context_geo: str | None) -> AgentAnswer:
    rt = system1.route(question, context_geo)
    if rt.decision == "REFUSE":
        return AgentAnswer(text=rt.refusal or "", route="REFUSED", escalation_reasons=rt.reasons)

    if rt.decision == "S1" and rt.geo_ids:                         # cue 4: data reliability
        anchor = repo().observations(rt.geo_ids[:1], HEADLINE)
        if _anchor_unreliable(anchor):
            rt.decision, rt.reasons = "S2", ["anchor_high_moe"]

    if rt.decision == "S1":
        return answer_s1(rt)

    try:
        text, obs, trace = await system2.run(question, {"intent": rt.intent, "geo_ids": rt.geo_ids,
                                                        "reasons": rt.reasons, "places": rt.places})
    except system2.NotConfigured:                                 # no LLM configured → degrade gracefully
        return _fallback(rt, "s2_unavailable")
    except Exception:                                             # timeout, 5xx, bad JSON … never a 500
        log.exception("System 2 failed; falling back to System 1")
        return _fallback(rt, "s2_error")
    text, bad = system2.redact_unsupported(text, obs)
    reasons = rt.reasons + (["unsupported_numbers_removed"] if bad else [])
    return AgentAnswer(text=text, route="S2", intent=rt.intent, geo_ids=rt.geo_ids,
                       observations=[Observation(**{k: v for k, v in o.items() if k in Observation.model_fields})
                                     for o in obs],
                       escalation_reasons=reasons, trace=[{"tool": t["tool"], "args": t["args"]} for t in trace])
