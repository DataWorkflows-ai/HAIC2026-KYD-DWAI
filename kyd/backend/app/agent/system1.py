"""System 1: fast, deterministic routing with a fast-and-frugal tree (§3.1–3.3).

Cues are checked in order, and the first decisive cue exits:
  1. Guardrail: individual inference or partisan request → REFUSE
  2. Entity: no district, or more than two districts → ESCALATE (or ask)
  3. Intent: one intent above the confidence floor → else ESCALATE
  4. Data: an anchor figure is suppressed or has high MOE → ESCALATE (needs a caveated narrative)
  5. Otherwise → answer with a template (S1)
"""
from __future__ import annotations
import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from ..config import settings

DOMINANT_SHARE = 0.6        # a place resolves to one district only if that district holds ≥ 60% of it

REFUSE_PATTERNS = [
    (r"\b(who|which (person|people|resident|household)s?)\b.*\b(on|receiv\w*|get\w*)\b.*\b(snap|welfare|benefits|medicaid|quest)\b",
     "individual"),
    (r"\b(name|address|phone|ssn|social security)\b.*\b(of|for)\b.*\b(resident|recipient|person)", "individual"),
    # Electoral advice and party politics. Voting RECORDS ("how did HD 22 vote on SB 123") are allowed.
    (r"\b(campaign\w*|candidates?|re-?elect\w*|elections?|electoral|incumbent|challenger|ballot|swing (district|seat)s?"
     r"|democrat\w*|republican\w*|partisan|endorse\w*)\b", "partisan"),
    (r"\b(should|who will|who would|who to|whom to|who do i|who should)\b.*\b(vote for|vote against|win|beat|lose|run for)\b",
     "partisan"),
    (r"\bvot\w* (for|against) (him|her|them|the (representative|senator|rep|incumbent))\b", "partisan"),
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
    places: list[dict] = field(default_factory=list)   # place names matched by the gazetteer, with candidates


@lru_cache
def gazetteer() -> dict[str, dict]:
    """Place names and ZIPs → districts, built by etl/load_places.py. Empty if the file is missing."""
    p = settings().data_dir / "place_aliases.json"
    return json.loads(p.read_text(encoding="utf-8"))["aliases"] if p.exists() else {}


def _chamber(t: str, context_geo: str | None) -> str:
    if re.search(r"\b(senate|senator|sd)\b", t):
        return "SD"
    if re.search(r"\b(house|representative|rep|hd)\b", t):
        return "HD"
    return "SD" if (context_geo or "").startswith("SD") else "HD"


def resolve_places(text: str, context_geo: str | None, aliases: dict[str, dict] | None = None) -> list[dict]:
    """Longest alias first, and a matched span is not matched again ("Waipio Acres" is not also "Waipio")."""
    aliases = gazetteer() if aliases is None else aliases
    t = normalize(text)
    ch = _chamber(t, context_geo)
    found = []
    for alias in sorted(aliases, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(alias)}\b", t)
        if not m:
            continue
        t = t[:m.start()] + " " * len(alias) + t[m.end():]
        a = aliases[alias]
        cands = a.get(ch) or []
        dominant = cands[0][0] if cands and cands[0][1] >= DOMINANT_SHARE and not a.get("ambiguous") else None
        found.append({"alias": alias, "name": a["name"], "chamber": ch, "dominant": dominant,
                      "candidates": [g for g, _ in cands]})
    return found


def resolve_districts(text: str, context_geo: str | None, places: list[dict] | None = None) -> list[str]:
    out = []
    for m in DISTRICT_RE.finditer(text):
        chamber = "SD" if m.group(1).lower() in ("senate", "sd", "senator") else "HD"
        n = int(m.group(3))
        if (chamber == "SD" and 1 <= n <= 25) or (chamber == "HD" and 1 <= n <= 51):
            out.append(f"{chamber}-{n:02d}")
    t = normalize(text)
    out.extend(p["dominant"] for p in places or [] if p["dominant"])
    if not out and not places and context_geo and re.search(r"\b(this|my|the) district\b|^\W*$", t + " this district"):
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


def route(text: str, context_geo: str | None = None, aliases: dict[str, dict] | None = None) -> Route:
    t = normalize(text)
    for pat, kind in REFUSE_PATTERNS:                                     # cue 1
        if re.search(pat, t):
            msg = ("I can only describe populations at the district level, not individual residents."
                   if kind == "individual" else
                   "I provide nonpartisan, population-level data only and can't advise on elections or candidates.")
            return Route("REFUSE", reasons=[f"guardrail:{kind}"], refusal=msg)

    places = resolve_places(text, context_geo, aliases)
    geos = resolve_districts(text, context_geo, places)                   # cue 2
    intent, conf, multi = classify(text)                                  # cue 3
    reasons = []
    if intent == "compare" and len(geos) == 1 and context_geo and context_geo not in geos:
        geos.append(context_geo)
    split = [p for p in places if not p["dominant"]]
    if split:
        reasons.append("place_spans_districts")
        if not geos:                                                      # hand the candidates to S2
            geos = list(dict.fromkeys(g for p in split for g in p["candidates"]))
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
        return Route("S2", intent, geos, reasons, places=places)
    return Route("S1", intent, geos, places=places)
