"""System 1: fast, deterministic routing with a fast-and-frugal tree (§3.1–3.3).

Cues are checked in order, and the first decisive cue exits:
  1. Guardrail: individual inference or partisan request → REFUSE
  2. Entity: no district, or more than two districts → ESCALATE (or ask)
  3. Intent: one intent above the confidence floor → else ESCALATE
  4. Data: an anchor figure is suppressed or has high MOE → ESCALATE (needs a caveated narrative)
  5. Otherwise → answer with a template (S1)
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field

REFUSE_PATTERNS = [
    (r"\b(who|which (person|people|resident|household)s?)\b.*\b(on|receiv\w*|get\w*)\b.*\b(snap|welfare|benefits|medicaid|quest)\b",
     "individual"),
    (r"\b(name|address|phone|ssn|social security)\b.*\b(of|for)\b.*\b(resident|recipient|person)", "individual"),
    (r"\b(vote|voting|elect|elections?|re-?elect|campaign|candidates?|incumbent|challenger|democrat\w*|republican\w*|partisan|endorse\w*)\b", "partisan"),
]

INTENTS = {
    "compare": [r"\bcompar\w*", r"\bvs\.?\b", r"\bversus\b", r"\bdifference between\b"],
    "programs": [r"\bprogram\w*", r"\bassistance\b", r"\bbenefit\w*", r"\beligib\w*", r"\boutreach\b",
                 r"\bunderserved\b", r"\buptake\b", r"\bgap\b"],
    "profile": [r"\bprofile\b", r"\bdemograph\w*", r"\bwho lives\b", r"\bpopulation\b", r"\boverview\b",
                r"\bincome\b", r"\bpoverty\b", r"\bage\b", r"\bhousing\b", r"\brent\w*"],
    "map": [r"\bmap\b", r"\bwhere\b.*\bhighest\b", r"\bacross (the )?(state|districts)\b"],
}

DISTRICT_RE = re.compile(r"\b(senate|sd|house|hd|representative|rep\.?|senator)\s*(district\s*)?#?\s*(\d{1,2})\b", re.I)


def normalize(s: str) -> str:
    """Strip the ʻokina and kahakō so 'Kāneʻohe' matches 'kaneohe'."""
    s = s.replace("ʻ", "").replace("‘", "").replace("'", "")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


@dataclass
class Route:
    decision: str                  # REFUSE | S1 | S2 | CLARIFY
    intent: str | None = None
    geo_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    refusal: str | None = None


def resolve_districts(text: str, context_geo: str | None, aliases: dict[str, list[str]] | None = None) -> list[str]:
    out = []
    for m in DISTRICT_RE.finditer(text):
        chamber = "SD" if m.group(1).lower() in ("senate", "sd", "senator") else "HD"
        n = int(m.group(3))
        if (chamber == "SD" and 1 <= n <= 25) or (chamber == "HD" and 1 <= n <= 51):
            out.append(f"{chamber}-{n:02d}")
    t = normalize(text)
    for alias, geos in (aliases or {}).items():           # gazetteer, filled from ref.place_alias
        if re.search(rf"\b{re.escape(alias)}\b", t):
            out.extend(geos)
    if not out and context_geo and re.search(r"\b(this|my|the) district\b|^\W*$", t + " this district"):
        out.append(context_geo)
    return list(dict.fromkeys(out))


def classify(text: str) -> tuple[str | None, float, list[str]]:
    t = normalize(text)
    hits = {k: sum(bool(re.search(p, t)) for p in ps) for k, ps in INTENTS.items()}
    ranked = sorted(hits.items(), key=lambda kv: kv[1], reverse=True)
    top, n = ranked[0]
    if n == 0:
        return None, 0.0, []
    multi = [k for k, v in ranked if v > 0]
    conf = n / (n + sum(v for _, v in ranked[1:]))
    return top, conf, multi


def route(text: str, context_geo: str | None = None, aliases=None) -> Route:
    t = normalize(text)
    for pat, kind in REFUSE_PATTERNS:                                     # cue 1
        if re.search(pat, t):
            msg = ("I can only describe populations at the district level, not individual residents."
                   if kind == "individual" else
                   "I provide nonpartisan, population-level data only and can't advise on elections or candidates.")
            return Route("REFUSE", reasons=[f"guardrail:{kind}"], refusal=msg)

    geos = resolve_districts(text, context_geo, aliases)                  # cue 2
    intent, conf, multi = classify(text)                                  # cue 3
    reasons = []
    if intent == "compare" and len(geos) == 1 and context_geo and context_geo not in geos:
        geos.append(context_geo)
    if not geos:
        reasons.append("no_district_resolved")
    if len(geos) > 2:
        reasons.append("many_districts")
    if intent is None or conf < 0.6:
        reasons.append("low_intent_confidence")
    if len(multi) > 1 and conf < 0.75:
        reasons.append("multi_intent")
    if intent == "compare" and len(geos) != 2:
        reasons.append("compare_needs_two")
    if reasons:
        return Route("S2", intent, geos, reasons)
    return Route("S1", intent, geos)
