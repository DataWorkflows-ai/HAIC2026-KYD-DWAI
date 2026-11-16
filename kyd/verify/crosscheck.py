"""Cross-source checks between independent publications of the same thing.

These are expected to agree only within a tolerance (different surveys, months, or selection
rules), so a miss is a WARN for a person to look at, not a FAIL. The comparisons that cannot be
expected to agree at all (survey estimate vs administrative count) are INFO, with the ratio shown.
"""
from __future__ import annotations
import csv
import json
import sqlite3
import sys
from collections import defaultdict

from census import load, num
from core import PROCESSED, REPO, Report, rel_close

COUNTY_OF = {"Oahu": "Honolulu", "Hawaii": "Hawaii", "Maui": "Maui", "Kauai": "Kauai"}


def _bessd() -> dict[tuple[str, str, str], dict]:
    rows = csv.DictReader((PROCESSED / "bessd_sfy2026_caseload_by_island.csv").open())
    return {(r["month"], r["metric"], r["code"]): r for r in rows}


def run(rep: Report) -> None:
    sys.path.insert(0, str(REPO / "scripts"))
    import load_county_snap, tanf_by_island  # noqa: E401
    b = _bessd()

    # 1. DHS testimony (Sept 2025) vs BESSD workbook (Sept 2025): same administrative system, same month
    rep.add("dhs.testimony_2025_10.archived", "dhs.testimony_2025_10", "provenance", "warn",
            "County SNAP figures in scripts/load_county_snap.py cite a capitol.hawaii.gov testimony PDF that is not "
            "archived in data/raw, so they cannot be re-read; they are checked against the BESSD workbook instead")
    code = {"Honolulu": "OB", "Hawaii": "HB", "Kauai": "KB", "Maui": "Maui", "Molokai": "Molokai", "Lanai": "Lanai"}
    for county, hh, persons, _ in load_county_snap.COUNTY_SNAP:
        bh = b.get(("2025-09", "households", code[county]))
        bp = b.get(("2025-09", "persons", code[county]))
        if not bh or not bp:
            rep.add(f"cross.snap_county.{county}", "dhs.testimony_2025_10", "cross_source", "warn",
                    f"no BESSD Sept 2025 row for {county}")
            continue
        got = (float(bh["total"]), float(bp["total"]))
        ok = rel_close(hh, got[0], 0.03) and rel_close(persons, got[1], 0.03)
        rep.add(f"cross.snap_county.{county}", "dhs.testimony_2025_10", "cross_source", "pass" if ok else "warn",
                f"{county} SNAP Sept 2025 households/persons: testimony vs BESSD workbook (±3%)",
                expected=list(got), actual=[hh, persons])

    # 2. Databook SFY 2025 average monthly SNAP cases vs BESSD SFY 2026 statewide households (adjacent years)
    sj = json.loads((PROCESSED / "dhs_snap_demographics_june2025.json").read_text())
    st = [float(v["total"]) for (m, met, c), v in b.items() if met == "households" and c == "STATE"]
    if st:
        avg = sum(st) / len(st)
        db_cases = sj["sfy_2025_caseload"]["avg_monthly_cases"]
        rep.add("cross.snap_cases_sfy25_vs_sfy26", "dhs.bessd_sfy2026", "cross_source",
                "pass" if rel_close(avg, db_cases, 0.10) else "warn",
                "Databook SFY 2025 average SNAP cases vs BESSD SFY 2026 average households (±10%, adjacent years)",
                expected=db_cases, actual=round(avg))

    # 3. ACS SNAP households (survey) vs BESSD households (administrative), by county — INFO
    counties = json.loads((REPO / "kyd" / "data" / "district_counties.json").read_text())
    _, s2201 = load("S2201", "house")
    acs = defaultdict(float)
    for d, r in s2201.items():
        acs[COUNTY_OF[counties[f"HD-{d:02d}"]]] += num(r["S2201_C03_001E"]) or 0
    months = sorted({m for m, _, _ in b})
    for county, c in (("Honolulu", "OB"), ("Hawaii", "HB"), ("Kauai", "KB"), ("Maui", "MB")):
        vals = [float(b[(m, "households", c)]["total"]) for m in months if (m, "households", c) in b]
        if vals:
            admin = sum(vals) / len(vals)
            rep.add(f"cross.snap_acs_vs_admin.{county}", "census.S2201", "cross_source", "info",
                    f"{county}: ACS 2020–24 SNAP households vs BESSD SFY 2026 average (survey/admin ratio "
                    f"{acs[county] / admin:.2f}; ACS typically undercounts SNAP receipt)",
                    expected=round(admin), actual=round(acs[county]))

    # 4. ACS poverty ladder (5-yr, districts summed) vs Databook ladder (1-yr 2024, statewide)
    pj = json.loads((PROCESSED / "dhs_databook_census_poverty_estimates.json").read_text())
    ladder = next((r for r in pj["individuals_below_percent_of_poverty_hawaii"] if r["year"] == 2024), None)
    _, s1701 = load("S1701", "house")
    for c, k, label in (("C01_038E", "pct_50", "50%"), ("C01_039E", "pct_125", "125%"), ("C01_040E", "pct_150", "150%"),
                        ("C01_041E", "pct_185", "185%"), ("C01_042E", "pct_200", "200%")):
        acs_sum = sum(num(r[f"S1701_{c}"]) or 0 for r in s1701.values())
        if ladder:
            rep.add(f"cross.poverty_ladder.{k}", "census.S1701", "cross_source",
                    "pass" if rel_close(acs_sum, ladder[k], 0.15) else "warn",
                    f"S1701 {c} summed over House districts (5-yr) vs Databook people below {label} of poverty "
                    f"(1-yr 2024), ±15%: confirms {c} is the {label} line",
                    expected=ladder[k], actual=round(acs_sum))

    # 5. ACS county poverty % (5-yr) vs Databook county poverty % (1-yr 2024)
    p24 = next((r for r in pj["population_in_poverty_percent_by_county"] if r["year"] == 2024), None)
    below, tot = defaultdict(float), defaultdict(float)
    for d, r in s1701.items():
        cty = COUNTY_OF[counties[f"HD-{d:02d}"]]
        below[cty] += num(r["S1701_C02_001E"]) or 0
        tot[cty] += num(r["S1701_C01_001E"]) or 0
    for cty, key in (("Honolulu", "honolulu"), ("Hawaii", "hawaii"), ("Kauai", "kauai"), ("Maui", "maui")):
        if p24 and tot[cty]:
            ours = 100 * below[cty] / tot[cty]
            rep.add(f"cross.poverty_pct.{cty}", "census.S1701", "cross_source",
                    "pass" if abs(ours - p24[key]) <= 3 else "warn",
                    f"{cty} poverty rate: districts summed (5-yr) vs Databook 2024 (1-yr), ±3 points",
                    expected=p24[key], actual=round(ours, 1))

    # 6. tanf_by_island.POPULATION vs the table it says it came from, and vs ACS
    db = sqlite3.connect(REPO / "data" / "districts.db")
    ch = {r[0]: r[2] for r in db.execute("SELECT * FROM county_housing")}
    for k, cty in (("OAHU", "Honolulu"), ("HAWAII", "Hawaii"), ("KAUAI", "Kauai"), ("MAUI", "Maui")):
        rep.expect(tanf_by_island.POPULATION[k] == ch.get(cty), f"cross.tanf_population.{k}", "scripts.tanf_by_island",
                   "transcription", f"tanf_by_island.POPULATION[{k}] equals districts.db county_housing",
                   expected=ch.get(cty), actual=tanf_by_island.POPULATION[k])
    _, dp05 = load("DP05", "house")
    pop = defaultdict(float)
    for d, r in dp05.items():
        pop[COUNTY_OF[counties[f"HD-{d:02d}"]]] += num(r["DP05_0001E"]) or 0
    for k, cty in (("OAHU", "Honolulu"), ("HAWAII", "Hawaii"), ("KAUAI", "Kauai"), ("MAUI", "Maui")):
        rep.add(f"cross.population.{k}", "scripts.tanf_by_island", "cross_source",
                "pass" if rel_close(pop[cty], tanf_by_island.POPULATION[k], 0.05) else "warn",
                f"{cty} population used for per-capita TANF vs ACS 2020–24 districts summed (±5%)",
                expected=round(pop[cty]), actual=tanf_by_island.POPULATION[k])
