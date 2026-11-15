"""System 2: an LLM that plans tool calls and writes the cited narrative (§3.4).

The model is provider-agnostic: Anthropic, or any OpenAI-compatible endpoint
(OpenAI, vLLM, llama.cpp). The LLM sees numbers only through tool results, and
the final text is checked so that every number in it comes from a returned
observation (§10.2).
"""
from __future__ import annotations
import json
import re
import httpx
from pydantic import BaseModel
from ..config import settings
from .tools import TOOL_SPECS, TOOLS

class NotConfigured(RuntimeError):
    """No LLM provider is configured (KYD_LLM_PROVIDER=none)."""


SYSTEM = """You are Know Your District, a nonpartisan assistant for Hawaiʻi legislative offices.
Rules:
- Use tools for every figure. Never state a number that a tool did not return.
- After each figure, cite it as [obs:<obs_id>].
- If a figure has the flag suppressed_cv or high_moe, say it is an uncertain estimate.
- Speak about populations only. Never about individuals. No partisan or electoral advice.
- Eligibility is informational. Point to the program's official_url for determinations.
- Use correct ʻokina and kahakō. Use plain language and keep answers under 200 words.
Geography ids: HI, CNTY-15001/15003/15007/15009, SD-01..SD-25, HD-01..HD-51."""


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
    found = []
    def walk(x):
        if isinstance(x, dict):
            if "obs_id" in x and "value" in x:
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return found


NUM = re.compile(r"(?<![\w-])\$?\d[\d,]*(?:\.\d+)?%?")
# Spans that hold numbers we never check: citation ids, district ids/names, years and year ranges.
_SKIP = re.compile(r"\[obs:[^\]]+\]|\b(?:SD|HD)-\d+\b|\bDistrict \d+\b|\b(?:19|20)\d{2}(?:[–-](?:19|20)\d{2})?\b")
REDACTED = "[figure removed: not from a cited source]"


def _allowed(obs: list[dict]) -> set[float]:
    allowed = set()
    for o in obs:
        for k in ("value", "moe"):
            v = o.get(k)
            if v is not None:
                allowed |= {round(float(v), 1), round(float(v)), round(float(v), 2)}
    return allowed


def _unsupported_spans(text: str, obs: list[dict]) -> list[tuple[int, int, str]]:
    allowed = _allowed(obs)
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


def redact_unsupported(text: str, obs: list[dict]) -> tuple[str, list[str]]:
    """Replace every unsupported number in place, so it never reaches the user, and say so once."""
    spans = _unsupported_spans(text, obs)
    if not spans:
        return text, []
    for a, b, _ in reversed(spans):
        text = text[:a] + REDACTED + text[b:]
    text += ("\n\n⚠ Some figures were removed because they could not be traced to a cited source. "
             "Ask again, or open the district profile for the sourced numbers.")
    return text, [s for _, _, s in spans]


async def run(question: str, hint: dict, max_steps: int = 6) -> tuple[str, list[dict], list[dict]]:
    s = settings()
    if s.llm_provider == "none":
        raise NotConfigured("no LLM configured")
    user = f"{question}\n\n(System 1 hint: {json.dumps(hint)})"
    trace: list[dict] = []
    if s.llm_provider == "anthropic":
        text = await _anthropic(user, trace, max_steps)
    else:
        text = await _openai_compat(user, trace, max_steps)
    obs = [o for t in trace for o in collect_obs(t.get("output"))]
    return text, obs, trace


async def _openai_compat(user: str, trace: list, max_steps: int) -> str:
    s = settings()
    base = s.llm_base_url or "https://api.openai.com/v1"
    tools = [{"type": "function", "function": t} for t in TOOL_SPECS]
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
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


async def _anthropic(user: str, trace: list, max_steps: int) -> str:
    s = settings()
    tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOL_SPECS]
    msgs = [{"role": "user", "content": user}]
    async with httpx.AsyncClient(timeout=120) as c:
        for _ in range(max_steps):
            r = await c.post("https://api.anthropic.com/v1/messages",
                             headers={"x-api-key": s.llm_api_key, "anthropic-version": "2023-06-01"},
                             json={"model": s.llm_model, "max_tokens": 1200, "system": SYSTEM,
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
