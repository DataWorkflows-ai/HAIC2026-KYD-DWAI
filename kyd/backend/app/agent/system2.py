"""System 2: an LLM that plans tool calls and writes the cited narrative (§3.4).

The model is provider-agnostic: Anthropic, or any OpenAI-compatible endpoint
(OpenAI, vLLM, llama.cpp). The LLM sees numbers only through tool results, and
the final text is checked so that every number in it comes from a returned
observation (§10.2).
"""
from __future__ import annotations
import json
import re
from functools import lru_cache
import httpx
from pydantic import BaseModel
from ..config import settings
from ..services.repo import repo
from .tools import TOOL_SPECS, TOOLS

class NotConfigured(RuntimeError):
    """No LLM provider is configured (KYD_LLM_PROVIDER=none)."""


SYSTEM = """You are Know Your District, a nonpartisan assistant for Hawaiʻi legislative offices.

Figures
- Use tools for every figure. Never state a number that a tool did not return, and never compute a new one.
- Quote only figures that come with an obs_id. Numbers inside text fields (rationale, notes, assumptions) are
  not citable; to use one, fetch it with get_district_profile (state: geo_id HI).
- After each figure, cite it as [obs:<obs_id>]. Give the ± margin when the tool returns one, and the source
  and years (for example "ACS 2020–2024").
- If a figure has the flag suppressed_cv or high_moe, say it is an uncertain estimate.
- To say whether two figures differ, use compare_district's `significant` result. Do not work out interval
  bounds (value minus or plus the margin) yourself.
- Labels marked ESTIMATE or est. are modelled or allocated, not counted: call them estimates.

Eligibility
- People "look eligible" or "may be eligible". Never write that people "are eligible", "qualify" or
  "are missing out". Say "not enrolled". The exception is an administrative count of people already certified,
  such as students eligible for free or reduced-price meals.
- For district SNAP gaps, use the ACS strict poverty-household figure from snap_gap_range or program_gaps:
  poverty households not reporting SNAP, with MOE. Say households, not people. For statewide SNAP, use USDA's
  people estimate and range. If the hint's reasons include snap_gap, call snap_gap_range or program_gaps.
- Eligibility is decided by the administering agency. Point to the program's official_url.
- DHS does not publish SNAP enrollment by district. When asked about SNAP enrollment, participation or how many
  people are on SNAP in a district, begin with exactly that sentence. Then give the share of households reporting
  SNAP (pct_snap_hh), and say it is self-reported on the Census survey, not DHS enrollment.

Context
- Crime, test scores, births and deaths, LIDAC, HUD housing and similar indicators describe a district. Never say
  that one indicator causes or explains another, or explains a program gap.

When there is no figure
- If no tool returns the figure asked for, say so in the first sentence. Do not swap in a different measure
  without saying so. Homelessness: KYD has no district figures; point-in-time counts are published by Partners
  in Care for Oʻahu and Bridging the Gap for Hawaiʻi, Maui and Kauaʻi counties. For other topics, name the
  publishing agency only if a tool result names it.

Places
- If the question names no place and the hint has no geo_ids, ask which district, for example "House District 22"
  or "Senate District 9". Do not answer with state figures unless asked for the state.
- "HD12", "house district 12" and "district 12 house" mean HD-12; "SD12" means SD-12; Oʻahu is CNTY-15003.
- For "which districts have the highest/lowest …", use rank_districts and mention not_reliably_different pairs.

Guardrails
- Speak about populations only, never about individuals.
- No partisan or electoral advice. If asked, reply: "I provide nonpartisan, population-level data only and
  can't advise on elections, parties or candidates."

Style
- Lead with the answer. Use correct ʻokina and kahakō. Plain language, under 200 words.

Documents
- When asked for a memo, brief, letter, talking points, report, fact sheet or other long-form writing, reply with
  one or two sentences, then the document inside <document title="Short title">…</document>, in Markdown
  (headings, bullet lists, tables). Up to 600 words. Every rule above applies inside the document, including
  [obs:<obs_id>] after each figure.
- Earlier turns in the conversation are context only. Fetch any figure again with a tool before using it.
Geography ids: HI, CNTY-15001/15003/15007/15009, SD-01..SD-25, HD-01..HD-51."""


@lru_cache
def system_prompt() -> str:
    """SYSTEM plus the indicator ids the tools accept (year-by-year trend series left out)."""
    inds = [i for i in repo().indicators() if not str(i.get("topic", "")).endswith("_trend")]
    return SYSTEM + "\nIndicator ids (pass to get_district_profile `indicators` or rank_districts):\n" + "\n".join(
        f"- {i['indicator']}: {i['label']}" for i in inds)


def _dump(x):
    if isinstance(x, BaseModel):
        return x.model_dump()
    if isinstance(x, list):
        return [_dump(i) for i in x]
    if isinstance(x, dict):
        return {k: _dump(v) for k, v in x.items()}
    return x


def call_tool(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return {"error": f"unknown tool {name}"}
    try:
        return {"result": _dump(TOOLS[name](**args))}
    except Exception as e:  # tool errors go back to the model, not to the user
        return {"error": f"{type(e).__name__}: {e}"}


def collect_obs(payload) -> list[dict]:
    """Observations in a tool result, including those an estimate cites only by id (input_obs_ids, context_obs_ids)."""
    found = []
    def walk(x):
        if isinstance(x, dict):
            if "obs_id" in x and "value" in x:
                found.append(x)
            for i in (x.get("input_obs_ids") or []) + (x.get("context_obs_ids") or []):
                if o := repo().observation(i):
                    found.append(o.model_dump())
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return found


def derived_values(payload) -> list[float]:
    """Estimates a tool computed from cited observations by a published rule (estimate_cross_program)."""
    out = []
    def walk(x):
        if isinstance(x, dict):
            if x.get("input_obs_ids"):
                out.extend(float(x[k]) for k in ("estimate", "low", "high") if isinstance(x.get(k), (int, float)))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return out


NUM = re.compile(r"(?<![\w-])\$?\d[\d,]*(?:\.\d+)?%?")
# Spans that hold numbers we never check: citation ids, district ids/names, years and year ranges.
_AGE = r"(?:1[5-9]|2[0-6]|3[045]|4[045]|5[0459]|6[02459]|7[0459]|8[045]|5|6)(?!\d)"
_SKIP = re.compile((r"\[obs:[^\]]+\]|\b(?:SD|HD)[\s-]?\d+\b|\bDistrict \d+\b"
                   r"|\b(?:SY\s?)?(?:19|20)\d{2}(?:[–-](?:(?:19|20)\d{2}|\d{2}))?\b"   # 2024, 2020–2024, SY2025–26
                   # program thresholds are rules, not data: "200% of poverty", "138% FPL"
                   r"|\b(?:100|125|130|135|138|150|185|200|250|300|400)%(?=\s*(?:of\s+(?:the\s+)?(?:federal\s+)?poverty|FPL|of\s+FPL))"
                   # the rent-burden definition and confidence levels: "30% or more of income", "90% margins"
                   r"|\b(?:30|35|50)(?:\.0)?%(?=\s*(?:\+|or more\b|of\s+(?:their\s+|household\s+)?income))"
                   r"|\b30(?:\.0)?%?\s*[–-]\s*34\.9%"                               # ACS rent-burden band
                   r"|\b9[05]%(?=\s+(?:confidence\s+)?(?:intervals?|margins?|level))"
                   r"|(?<=\bper )(?:1,000|10,000|100,000)\b"                          # rate units
                   r"|\b(?:51|25)(?=\s+(?:House\s+|Senate\s+)?districts\b)"            # chamber sizes
                   # age groups name a population, they are not figures: "65 and older", "under 18", "18–64", "60+".
                   # Only the standard Census/program cut-points, and never when a % follows.
                   + "|" + r"(?<![\w,.$-])@AGE@\+(?![\w%])"
                   + "|" + r"(?<![\w,.$-])@AGE@(?:\s+years?)?\s+(?:and|or)\s+(?:older|over|younger|under)\b"
                   + "|" + r"\b(?:ages?|aged|under|over)\s+@AGE@(?:\s*(?:[–-]|to|and)\s*@AGE@)?(?!\d|[,.]\d|\s*%)"
                   + "|" + r"(?<![\w,.$-])@AGE@\s*[–-]\s*@AGE@(?!\d|[,.]\d|\s*%)").replace("@AGE@", _AGE))
REDACTED = "[figure removed: not from a cited source]"


def _allowed(obs: list[dict], extra: list[float] = ()) -> set[float]:
    allowed = set()
    vals = [o.get(k) for o in obs for k in ("value", "moe", "cv")] + list(extra)
    for v in vals:
        if v is not None:
            allowed |= {round(float(v), 1), round(float(v)), round(float(v), 2)}
    return allowed


def _unsupported_spans(text: str, obs: list[dict], extra: list[float] = ()) -> list[tuple[int, int, str]]:
    allowed = _allowed(obs, extra)
    skip = [m.span() for m in _SKIP.finditer(text)]
    out = []
    for m in NUM.finditer(text):
        if any(a <= m.start() < b for a, b in skip):
            continue
        n = float(m.group().strip("$%").replace(",", ""))
        if n in allowed or round(n, 1) in allowed or round(n) in allowed or n < 10 and n.is_integer():
            continue
        out.append((m.start(), m.end(), m.group()))
    return out


def unsupported_numbers(text: str, obs: list[dict]) -> list[str]:
    """Numbers in the text that do not match any returned value or MOE.
    District numbers, years, citation ids and small counts (< 10) are ignored."""
    return [s for _, _, s in _unsupported_spans(text, obs)]


def redact_unsupported(text: str, obs: list[dict], extra: list[float] = ()) -> tuple[str, list[str]]:
    """Replace every unsupported number in place, so it never reaches the user, and say so once."""
    spans = _unsupported_spans(text, obs, extra)
    if not spans:
        return text, []
    for a, b, _ in reversed(spans):
        text = text[:a] + REDACTED + text[b:]
    text += ("\n\n⚠ Some figures were removed because they could not be traced to a cited source. "
             "Ask again, or open the district profile for the sourced numbers.")
    return text, [s for _, _, s in spans]


DOCUMENT = re.compile(r'<document(?:\s+title="([^"]{0,200})")?\s*>(.*?)(?:</document>|$)', re.S)


def split_document(text: str) -> tuple[str, dict | None]:
    """Pull a <document title="…">markdown</document> block out of the answer text."""
    m = DOCUMENT.search(text)
    if not m:
        return text, None
    rest = (text[:m.start()] + text[m.end():]).strip()
    return rest or "The document is in the panel.", {"title": (m.group(1) or "Document").strip(),
                                                      "body": m.group(2).strip()}


def _turns(history: list[tuple[str, str]] | None) -> list[dict]:
    out = []
    for q, a in history or []:
        out += [{"role": "user", "content": q}, {"role": "assistant", "content": a or "(no answer)"}]
    return out


async def run(question: str, hint: dict, max_steps: int = 6,
              history: list[tuple[str, str]] | None = None) -> tuple[str, list[dict], list[dict]]:
    s = settings()
    if s.llm_provider == "none":
        raise NotConfigured("no LLM configured")
    user = f"{question}\n\n(System 1 hint: {json.dumps(hint)})"
    trace: list[dict] = []
    if s.llm_provider == "anthropic":
        text = await _anthropic(user, trace, max_steps, _turns(history))
    else:
        text = await _openai_compat(user, trace, max_steps, _turns(history))
    obs = [o for t in trace for o in collect_obs(t.get("output"))]
    return text, obs, trace


async def _openai_compat(user: str, trace: list, max_steps: int, prior: list[dict] = ()) -> str:
    s = settings()
    base = s.llm_base_url or "https://api.openai.com/v1"
    tools = [{"type": "function", "function": t} for t in TOOL_SPECS]
    msgs = [{"role": "system", "content": system_prompt()}, *prior, {"role": "user", "content": user}]
    async with httpx.AsyncClient(timeout=120) as c:
        for _ in range(max_steps):
            r = await c.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {s.llm_api_key}"},
                             json={"model": s.llm_model, "messages": msgs, "tools": tools, "temperature": 0})
            r.raise_for_status()
            m = r.json()["choices"][0]["message"]
            msgs.append(m)
            if not m.get("tool_calls"):
                return m.get("content") or ""
            for tc in m["tool_calls"]:
                args = json.loads(tc["function"]["arguments"] or "{}")
                out = call_tool(tc["function"]["name"], args)
                trace.append({"tool": tc["function"]["name"], "args": args, "output": out})
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, default=str)[:30000]})
    return "I couldn't complete this within the tool-call budget."


async def _anthropic(user: str, trace: list, max_steps: int, prior: list[dict] = ()) -> str:
    s = settings()
    tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOL_SPECS]
    msgs = [*prior, {"role": "user", "content": user}]
    async with httpx.AsyncClient(timeout=120) as c:
        for _ in range(max_steps):
            r = await c.post("https://api.anthropic.com/v1/messages",
                             headers={"x-api-key": s.llm_api_key, "anthropic-version": "2023-06-01"},
                             json={"model": s.llm_model, "max_tokens": 3000, "system": system_prompt(),
                                   "tools": tools, "messages": msgs})
            r.raise_for_status()
            d = r.json()
            msgs.append({"role": "assistant", "content": d["content"]})
            uses = [b for b in d["content"] if b["type"] == "tool_use"]
            if not uses:
                return "".join(b.get("text", "") for b in d["content"] if b["type"] == "text")
            results = []
            for u in uses:
                out = call_tool(u["name"], u["input"])
                trace.append({"tool": u["name"], "args": u["input"], "output": out})
                results.append({"type": "tool_result", "tool_use_id": u["id"],
                                "content": json.dumps(out, default=str)[:30000]})
            msgs.append({"role": "user", "content": results})
    return "I couldn't complete this within the tool-call budget."
