"""Verify the program data sources. Run from the repo root:

  python kyd/verify/run.py            # run all checks, write kyd/data/verification_report.json
  python kyd/verify/run.py --accept   # same, then record current file hashes as verified (only if no FAIL)

Exit code: 0 = no FAIL, 1 = at least one FAIL. WARN never fails the run; it is listed for review.

When a source file is replaced (new Databook, new Census pull, new BESSD workbook), its hash no
longer matches manifest.json, so the report flags it as changed. The format and transcription
checks then show whether the new file still has the shape the scripts assume. Run --accept only
after reviewing the report.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import MANIFEST, RAW, PROCESSED, REPO, REPORT, Report, load_manifest, sha256  # noqa: E402
import bessd, census, crosscheck, databook, usda  # noqa: E402,E401

SOURCES = {  # id → file, publisher, how it's used
    "dhs.databook2025": {"path": RAW / "DHS-Databook-2025.pdf", "publisher": "Hawaiʻi DHS",
                         "url": "https://humanservices.hawaii.gov/wp-content/uploads/2026/03/DHS-Databook-2025.pdf",
                         "used_by": "aabd.py, ga_proxy.py, tanf_underenrollment.py, medquest.py, tanf_by_island.py"},
    "dhs.bessd_sfy2026": {"path": RAW / "SFY-2026-SUMMARY.numbers", "publisher": "Hawaiʻi DHS BESSD",
                          "url": None, "used_by": "tanf_by_island.py, load_county_snap.py (via data/processed CSV)"},
    "processed.snap_demographics": {"path": PROCESSED / "dhs_snap_demographics_june2025.json", "publisher": "derived from Databook p6",
                                    "url": None, "used_by": "map_data.py, app.py"},
    "processed.poverty_estimates": {"path": PROCESSED / "dhs_databook_census_poverty_estimates.json",
                                    "publisher": "derived from Databook p12–13", "url": None, "used_by": "tanf_by_island.py"},
    "processed.bessd_csv": {"path": PROCESSED / "bessd_sfy2026_caseload_by_island.csv", "publisher": "derived from BESSD workbook",
                            "url": None, "used_by": "tanf_by_island.py, load_county_snap.py"},
    "usda.snap_rates_fy2022": {"path": usda.PDF, "publisher": "USDA FNS (Mathematica)",
                               "url": "https://www.fns.usda.gov/sites/default/files/resource-files/ear-SNAP-Participation-Rates-2022.pdf",
                               "used_by": "kyd/etl/load_programs.py (SNAP gap range, benchmark end)"},
    **{f"census.{t}.{ch}": {"path": RAW / f"{t}_{ch}_districts.json", "publisher": "U.S. Census Bureau, ACS 2020–2024 5-year",
                            "url": f"https://data.census.gov/table/ACSST5Y2024.{t}", "used_by": "scripts/*.py"}
       for t, chs in census.TABLES.items() for ch in chs},
}


def provenance(rep: Report) -> dict:
    man = load_manifest()
    out = {}
    for sid, s in SOURCES.items():
        p: Path | None = s["path"]
        info = {k: (v.relative_to(REPO).as_posix() if isinstance(v, Path) else v) for k, v in s.items()}
        if p is None or not p.exists():
            info["sha256"] = None
            out[sid] = info
            continue
        h = sha256(p)
        info["sha256"] = h
        prev = man.get(p.relative_to(REPO).as_posix())
        info["verified_at"] = prev and prev.get("verified_at")
        if prev is None:
            rep.add(f"provenance.{sid}.new", sid, "provenance", "warn",
                    f"{p.name} has never been accepted; review the checks, then run --accept")
        elif prev["sha256"] != h:
            rep.add(f"provenance.{sid}.changed", sid, "provenance", "warn",
                    f"{p.name} changed since it was verified on {prev['verified_at']}; checks below show whether its "
                    f"format still matches", expected=prev["sha256"][:12], actual=h[:12])
        else:
            rep.ok(f"provenance.{sid}.unchanged", sid, "provenance", f"{p.name} unchanged since {prev['verified_at']}")
        out[sid] = info
    return out


def main(argv: list[str]) -> int:
    rep = Report()
    sources = provenance(rep)
    for mod in (census, databook, bessd, crosscheck, usda):
        try:
            mod.run(rep)
        except Exception as e:  # a crashed checker is itself a failure, never a silent skip
            rep.add(f"{mod.__name__}.crashed", mod.__name__, "format", "fail", f"{type(e).__name__}: {e}")
    out = rep.to_json(sources)
    REPORT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    s = out["summary"]
    print(f"verification: {s['pass']} pass, {s['info']} info, {s['warn']} warn, {s['fail']} fail → {REPORT.relative_to(REPO)}")
    for c in out["checks"]:
        if c["status"] in ("fail", "warn"):
            print(f"  {c['status'].upper():4} {c['id']}: {c['detail']}"
                  + (f" | expected {c['expected']} got {c['actual']}" if c["expected"] is not None or c["actual"] is not None else ""))
    if "--accept" in argv:
        if s["fail"]:
            print("not accepted: fix the FAIL checks first")
            return 1
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        old = load_manifest()
        man = {v["path"]: (old[v["path"]] if old.get(v["path"], {}).get("sha256") == v["sha256"]
                           else {"sha256": v["sha256"], "verified_at": now}) for v in sources.values() if v.get("sha256")}
        MANIFEST.write_text(json.dumps(man, indent=1, sort_keys=True))
        print(f"accepted {len(man)} source files → {MANIFEST.relative_to(REPO)}")
    return 1 if s["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
