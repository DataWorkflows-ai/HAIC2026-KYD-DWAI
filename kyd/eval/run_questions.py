"""Run the staffer question set through the agent and check each answer against its rules.

    python kyd/eval/run_questions.py [--only q01,q29] [--concurrency 4]

Needs an LLM (KYD_LLM_PROVIDER, KYD_LLM_MODEL, KYD_LLM_API_KEY); without one, System 2 questions fall back to
templates and are reported as such. Calls the agent in-process, so nothing is written to the audit log.
Writes kyd/eval/last_run.json and exits 1 if any check fails.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from app.agent import orchestrator, system2  # noqa: E402
from app.config import settings  # noqa: E402

# "Students eligible for free/reduced-price meals" is an administrative count of certified students, so allowed.
FORBIDDEN = [(r"\b(people|residents|households|families|kūpuna|kupuna|children|seniors|they|many|\d[\d,]*)\s+"
              r"(\w+\s+)?(are|is) (all |likely |probably |definitely )?eligible\b(?![^.\n]*\bmeals?\b)",
              "says people 'are eligible'"),
             (r"\bmissing out\b", "says 'missing out'"),
             (re.escape(system2.REDACTED), "a figure was removed as unsourced")]
ASKS_DISTRICT = re.compile(r"which (house |senate )?district|name a district|what district", re.I)
SNAP_LOW, SNAP_HIGH = {"snap_gap_low_persons", "pct_snap_gap_low"}, {"snap_gap_persons", "pct_snap_gap"}


def check(spec: dict, a) -> list[str]:
    text, inds = a.text, {o.indicator for o in a.observations}
    bad = [why for pat, why in FORBIDDEN if re.search(pat, text, re.I)]
    if spec.get("refuse"):
        return bad + ([] if a.route == "REFUSED" else [f"not refused (route {a.route})"])
    if a.route == "REFUSED":
        return bad + ["refused a question it should answer"]
    if spec.get("asks_district") and not (ASKS_DISTRICT.search(text) and "[obs:" not in text):
        bad.append("did not ask which district")
    if (p := spec.get("starts")) and not text.lstrip().lower().startswith(p.lower()):
        bad.append(f"does not start with “{p}”")
    first = re.split(r"(?<=[.!?])\s", text.strip().lstrip("*# "), maxsplit=1)[0]
    if (p := spec.get("first_sentence")) and not re.search(p, first, re.I):
        bad.append(f"first sentence does not match /{p}/")
    for i in spec.get("cites", []):
        if i not in inds:
            bad.append(f"does not cite {i}")
    for i in spec.get("not_cites", []):
        if i in inds:
            bad.append(f"cites {i}")
    if spec.get("cites_any") and "[obs:" not in text:
        bad.append("no citations")
    if (n := spec.get("min_geos")) and len({o.geo_id for o in a.observations if o.indicator in spec["cites"]}) < n:
        bad.append(f"fewer than {n} districts cited")
    if spec.get("snap_range") and not (inds & SNAP_LOW and inds & SNAP_HIGH):
        bad.append("does not give both ends of the SNAP gap range")
    bad += [f"missing /{p}/" for p in spec.get("contains", []) if not re.search(p, text, re.I)]
    bad += [f"contains /{p}/" for p in spec.get("absent", []) if re.search(p, text, re.I)]
    return bad


async def run_one(spec: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        t0 = time.perf_counter()
        a = await orchestrator.ask(spec["q"], None)
        fails = check(spec, a)
        return {"id": spec["id"], "question": spec["q"], "route": a.route, "pass": not fails, "failures": fails,
                "seconds": round(time.perf_counter() - t0, 1), "escalation_reasons": a.escalation_reasons,
                "cited": sorted({o.indicator for o in a.observations}), "answer": a.text}


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args(argv)
    specs = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    if args.only:
        keep = set(args.only.split(","))
        specs = [s for s in specs if s["id"] in keep]
    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*(run_one(s, sem) for s in specs))
    s = settings()
    for r in results:
        print(f"{'PASS' if r['pass'] else 'FAIL'} {r['id']} [{r['route']}] {r['question']}")
        for f in r["failures"]:
            print(f"     - {f}")
    n = sum(r["pass"] for r in results)
    print(f"\n{n}/{len(results)} passed  (LLM: {s.llm_provider} {s.llm_model})")
    if not args.only:
        (HERE / "last_run.json").write_text(json.dumps(
            {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "llm": f"{s.llm_provider} {s.llm_model}",
             "passed": n, "total": len(results), "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
