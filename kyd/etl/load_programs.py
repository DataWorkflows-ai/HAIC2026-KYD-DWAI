"""Program-analysis indicators (Crystal's scripts/ capabilities) → kyd/data/kyd.sqlite.

Run after load_acs_profile.py (which rebuilds the database; it calls this at the end):

  python kyd/etl/load_programs.py

Reads the archived ACS 2020–2024 subject tables in data/raw (S1701 poverty, S2201 SNAP) with the
same helpers and columns as scripts/snap_gap.py, tanf_proxy.py and ga_proxy.py, so the app shows
the figures her analyses compute (kyd/tests/test_programs_etl.py checks they agree district by
district). Counts carry Census MOEs; derived values carry approximate MOEs and a method note.

Idempotent: rows for the indicators and sources below are replaced on each run.

State values are DERIVED from the 51 House districts (which partition the state): counts summed,
MOE root-sum-of-squares; rates = summed numerators ÷ summed universes.
"""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
DB = REPO / "kyd" / "data" / "kyd.sqlite"
sys.path.insert(0, str(REPO / "scripts"))
from snap_gap import _load, _num, _district_number  # noqa: E402  Crystal's parsing, reused as-is

VINTAGE = "2020-2024"
ACS_URL = "https://data.census.gov/table/ACSST5Y2024.{t}"
SOURCES = {
    "acs5_2024_s1701_sld": ("S1701", "ACS 2020–2024 5-year S1701 Poverty Status, Hawaiʻi State Legislative Districts"),
    "acs5_2024_s2201_sld": ("S2201", "ACS 2020–2024 5-year S2201 Food Stamps/SNAP, Hawaiʻi State Legislative Districts"),
}
S1701, S2201 = "acs5_2024_s1701_sld", "acs5_2024_s2201_sld"
USDA = "usda_snap_rates_fy2022"
USDA_PDF = RAW / "research" / "usda" / "ear-SNAP-Participation-Rates-2022.pdf"
USDA_TITLE = ("Cunnyngham (2025), Reaching Those in Need: Estimates of State SNAP Participation Rates in FY 2022, "
              "technical report (Mathematica for USDA)")
USDA_URL = "https://www.fns.usda.gov/sites/default/files/resource-files/ear-SNAP-Participation-Rates-2022.pdf"
# Hawaiʻi, FY 2022, transcribed from USDA_PDF (printed page numbers):
SNAP_ELIGIBLE_HI = (161_104, round(1.645 * 9_424))   # Table A.18 p50: eligible people, SE 9,424 → 90% MOE
SNAP_PARTICIPANTS_HI = 130_188                       # Table A.3 p35: eligible participants, monthly average
SNAP_RATE_HI, SNAP_RATE_CI_HI = 81, (73, 88)         # Table III.1 p11; 90% interval Table III.3 p15
SNAP_RATE_US = 88                                    # national rate, report summary

# key: label, unit, topic, acs line(s), source
INDICATORS = {
    "pop_below_200fpl": ("People below 200% of poverty", "count", "program", "S1701_C01_042", S1701),
    "pct_below_200fpl": ("People below 200% of poverty (SNAP income proxy)", "pct", "program", "S1701_C01_042/C01_001", S1701),
    "snap_hh_count": ("Households receiving SNAP", "count", "program", "S2201_C03_001", S2201),
    "snap_persons_est": ("People in SNAP households (est.)", "count", "program", "S2201_C03_001×DP02_0016", S2201),
    "snap_gap_persons": ("Below 200% of poverty, not in SNAP households (est.)", "count", "program",
                         "S1701_C01_042−S2201_C03_001×DP02_0016", S2201),
    "pct_snap_gap": ("Share of people below 200% of poverty not reached by SNAP (est.)", "pct", "program",
                     "(S1701_C01_042−SNAP persons)/S1701_C01_042", S2201),
    "children_below_fpl": ("Related children under 18 below poverty (TANF proxy)", "count", "program", "S1701_C02_005", S1701),
    "pct_children_below_fpl": ("Related children under 18 below poverty (TANF proxy)", "pct", "program",
                               "S1701_C02_005/C01_005", S1701),
    "adults_18_64_below_fpl": ("Adults 18–64 below poverty (GA proxy)", "count", "program", "S1701_C02_006", S1701),
    "pct_adults_18_64_below_fpl": ("Adults 18–64 below poverty (GA proxy)", "pct", "program", "S1701_C02_006/C01_006", S1701),
    # inputs for cross-program estimates (app/services/crosswalk.py)
    "snap_hh_children": ("SNAP households with children under 18", "count", "program", "S2201_C03_009", S2201),
    "snap_hh_60plus": ("SNAP households with someone 60+", "count", "program", "S2201_C03_002", S2201),
    "snap_hh_disability": ("SNAP households with someone with a disability", "count", "program", "S2201_C03_023", S2201),
    "pop_below_125fpl": ("People below 125% of poverty", "count", "program", "S1701_C01_039", S1701),
    "pop_below_150fpl": ("People below 150% of poverty", "count", "program", "S1701_C01_040", S1701),
    "pop_below_185fpl": ("People below 185% of poverty", "count", "program", "S1701_C01_041", S1701),
    "pop_below_138fpl": ("People below 138% of poverty (est.)", "count", "program", "S1701_C01_039..040 interpolated", S1701),
    "pct_below_138fpl": ("People below 138% of poverty (Med-QUEST adult limit, est.)", "pct", "program",
                         "S1701_C01_039..040 interpolated / C01_001", S1701),
    # SNAP gap range. High end = snap_gap_persons (survey-based); low end = USDA benchmark, allocated to districts.
    "snap_gap_low_persons": ("Look eligible for SNAP, not participating: low end, benchmark-based (est.)", "count",
                             "program", "USDA HI eligible − participants, allocated by SNAP persons", USDA),
    "pct_snap_gap_low": ("SNAP gap, low end: share of people below 200% of poverty (est.)", "pct", "program",
                         "snap_gap_low_persons / S1701_C01_042", USDA),
    "snap_eligible_usda": ("People eligible for SNAP (USDA estimate, FY 2022)", "count", "program", "USDA Table A.18", USDA),
    "snap_participants_usda": ("Eligible people receiving SNAP (USDA estimate, FY 2022)", "count", "program",
                               "USDA Table A.3", USDA),
    "snap_participation_rate": ("SNAP participation rate among eligible people (USDA, FY 2022)", "pct", "program",
                                "USDA Table III.1", USDA),
    "snap_participation_rate_ci_low": ("SNAP participation rate, lower bound of 90% interval (USDA, FY 2022)", "pct",
                                       "program", "USDA Table III.3", USDA),
    "snap_participation_rate_ci_high": ("SNAP participation rate, upper bound of 90% interval (USDA, FY 2022)", "pct",
                                        "program", "USDA Table III.3", USDA),
    "snap_participation_rate_us": ("SNAP participation rate among eligible people, United States (USDA, FY 2022)", "pct",
                                   "program", "USDA report summary", USDA),
}
# Only the state has the USDA benchmark rows; districts get the allocated low end.
STATE_ONLY = ("snap_eligible_usda", "snap_participants_usda", "snap_participation_rate", "snap_participation_rate_ci_low",
              "snap_participation_rate_ci_high", "snap_participation_rate_us")
NOTE_138 = ("Linear interpolation between the 125% and 150% poverty-ratio counts (S1701 has no 138% line); "
            "MOE taken from the 150% line. Census poverty thresholds are national, not the higher Hawaiʻi guidelines "
            "Med-QUEST uses, so this likely understates the income-eligible pool.")
NOTE_PERSONS = ("SNAP households × district average household size (DP02_0016), as in scripts/snap_gap.py; "
                "MOE approximated from both MOEs. SNAP households are often larger than average, so this may understate.")
NOTE_GAP = ("People below 200% FPL minus estimated SNAP persons (scripts/snap_gap.py person-level gap). "
            "Proxy only: SNAP eligibility also depends on assets, household makeup and immigration status. "
            "MOE root-sum-of-squares.")
NOTE_GAP_PCT = "snap_gap_persons ÷ pop_below_200fpl. Proxy, not a measured eligible-but-not-enrolled rate; MOE not computed."
NOTE_GAP_LOW = ("Low end of the SNAP gap range, grade C (allocated from a state figure). USDA estimates 161,104 Hawaiʻi "
                "residents eligible under federal rules and 130,188 eligible participants in FY 2022; the difference is "
                "shared among districts by their estimated SNAP persons. Assumes every district participates at the "
                "state rate, so it cannot show which districts lag. MOE not computed.")
NOTE_GAP_LOW_PCT = "snap_gap_low_persons ÷ pop_below_200fpl, the same denominator as the high end. MOE not computed."
NOTE_USDA = ("Transcribed from the USDA technical report (Cunnyngham 2025, Mathematica). Federal eligibility rules; "
             "monthly average for FY 2022.")


def _table(name: str, chamber: str) -> dict[int, dict]:
    header, rows = _load(RAW / f"{name}_{chamber}_districts.json")
    out = {}
    for row in rows:
        n = _district_number(row[header.index("NAME")])
        if n is not None:
            out[n] = {header[i]: row[i] for i in range(len(header))}
    return out


def _em(row: dict, col: str) -> tuple[float | None, float | None]:
    return _num(row.get(col + "E")), _num(row.get(col + "M"))


def _pct(num: tuple, den: tuple) -> tuple[float | None, float | None]:
    """Census proportion MOE (ACS handbook): sqrt(MOEx² − p²·MOEy²)/Y, ratio formula if the radicand is negative."""
    (x, mx), (y, my) = num, den
    if x is None or not y:
        return None, None
    p = x / y
    if mx is None or my is None:
        return round(100 * p, 1), None
    r = mx ** 2 - p ** 2 * my ** 2
    m = math.sqrt(r if r >= 0 else mx ** 2 + p ** 2 * my ** 2) / y
    return round(100 * p, 1), round(100 * m, 1)


def district_values(chamber: str) -> dict[int, dict[str, tuple]]:
    s1701, s2201, dp02 = _table("S1701", chamber), _table("S2201", chamber), _table("DP02", chamber)
    out = {}
    for n, r in s1701.items():
        v: dict[str, tuple] = {}
        below200, univ = _em(r, "S1701_C01_042"), _em(r, "S1701_C01_001")
        v["pop_below_200fpl"] = below200
        v["pct_below_200fpl"] = _pct(below200, univ)
        kids = _em(r, "S1701_C02_005")
        v["children_below_fpl"] = kids
        v["pct_children_below_fpl"] = _pct(kids, _em(r, "S1701_C01_005"))
        adults = _em(r, "S1701_C02_006")
        v["adults_18_64_below_fpl"] = adults
        v["pct_adults_18_64_below_fpl"] = _pct(adults, _em(r, "S1701_C01_006"))
        for k, col in (("pop_below_125fpl", "S1701_C01_039"), ("pop_below_150fpl", "S1701_C01_040"),
                       ("pop_below_185fpl", "S1701_C01_041")):
            v[k] = _em(r, col)
        a, b = v["pop_below_125fpl"][0], v["pop_below_150fpl"][0]
        if a is not None and b is not None:
            est = round(a + (b - a) * (138 - 125) / (150 - 125))
            v["pop_below_138fpl"] = (est, v["pop_below_150fpl"][1])
            v["pct_below_138fpl"] = (_pct((est, None), univ)[0], None)
        if n in s2201:
            for k, col in (("snap_hh_children", "S2201_C03_009"), ("snap_hh_60plus", "S2201_C03_002"),
                           ("snap_hh_disability", "S2201_C03_023")):
                v[k] = _em(s2201[n], col)
        if n in s2201 and n in dp02:
            hh, hhm = _em(s2201[n], "S2201_C03_001")
            size, sizem = _em(dp02[n], "DP02_0016")
            v["snap_hh_count"] = (hh, hhm)
            if hh is not None and size is not None:
                persons = round(hh * size)
                pm = math.sqrt((hh * (sizem or 0)) ** 2 + (size * (hhm or 0)) ** 2)
                v["snap_persons_est"] = (persons, round(pm))
                if below200[0] is not None:
                    gap = below200[0] - persons
                    v["snap_gap_persons"] = (gap, round(math.sqrt(pm ** 2 + (below200[1] or 0) ** 2)))
                    v["pct_snap_gap"] = (round(100 * gap / below200[0], 1) if below200[0] else None, None)
        out[n] = v
    return out


SNAP_NOT_PARTICIPATING_HI = SNAP_ELIGIBLE_HI[0] - SNAP_PARTICIPANTS_HI


def add_low_end(vals: dict[int, dict[str, tuple]]) -> None:
    """Share USDA's statewide count of eligible non-participants among one chamber's districts by SNAP persons,
    so each chamber sums to the USDA figure (up to rounding)."""
    total = sum(d["snap_persons_est"][0] for d in vals.values() if "snap_persons_est" in d)
    for d in vals.values():
        if "snap_persons_est" not in d or not total:
            continue
        low = round(SNAP_NOT_PARTICIPATING_HI * d["snap_persons_est"][0] / total)
        d["snap_gap_low_persons"] = (low, None)
        below = d["pop_below_200fpl"][0]
        d["pct_snap_gap_low"] = (round(100 * low / below, 1) if below else None, None)


def state_values(house: dict[int, dict[str, tuple]]) -> dict[str, tuple]:
    def tot(k):
        xs = [d[k] for d in house.values() if k in d and d[k][0] is not None]
        return sum(x[0] for x in xs), math.sqrt(sum((x[1] or 0) ** 2 for x in xs))

    s1701 = _table("S1701", "house")
    def utot(col):
        return sum(_num(r.get(col + "E")) or 0 for r in s1701.values()), None

    out = {k: tot(k) for k in ("pop_below_200fpl", "snap_hh_count", "snap_persons_est", "snap_gap_persons",
                               "children_below_fpl", "adults_18_64_below_fpl", "snap_hh_children", "snap_hh_60plus",
                               "snap_hh_disability", "pop_below_125fpl", "pop_below_150fpl", "pop_below_185fpl",
                               "pop_below_138fpl")}
    out["pct_below_138fpl"] = (_pct((out["pop_below_138fpl"][0], None), utot("S1701_C01_001"))[0], None)
    out["pct_below_200fpl"] = (_pct((out["pop_below_200fpl"][0], None), utot("S1701_C01_001"))[0], None)
    out["pct_children_below_fpl"] = (_pct((out["children_below_fpl"][0], None), utot("S1701_C01_005"))[0], None)
    out["pct_adults_18_64_below_fpl"] = (_pct((out["adults_18_64_below_fpl"][0], None), utot("S1701_C01_006"))[0], None)
    out["pct_snap_gap"] = (round(100 * out["snap_gap_persons"][0] / out["pop_below_200fpl"][0], 1), None)
    out["snap_gap_low_persons"] = (SNAP_NOT_PARTICIPATING_HI, None)
    out["pct_snap_gap_low"] = (round(100 * SNAP_NOT_PARTICIPATING_HI / out["pop_below_200fpl"][0], 1), None)
    out["snap_eligible_usda"] = SNAP_ELIGIBLE_HI
    out["snap_participants_usda"] = (SNAP_PARTICIPANTS_HI, None)
    out["snap_participation_rate"] = (SNAP_RATE_HI, None)
    out["snap_participation_rate_ci_low"] = (SNAP_RATE_CI_HI[0], None)
    out["snap_participation_rate_ci_high"] = (SNAP_RATE_CI_HI[1], None)
    out["snap_participation_rate_us"] = (SNAP_RATE_US, None)
    return {k: (round(v), round(m) if m else None) if INDICATORS[k][1] == "count" else (v, m) for k, (v, m) in out.items()}


def _method(key: str, geo: str) -> tuple[str, str | None]:
    if key in STATE_ONLY:
        return "direct", NOTE_USDA
    if key == "snap_gap_low_persons":
        return "derived", NOTE_GAP_LOW
    if key == "pct_snap_gap_low":
        return "derived", NOTE_GAP_LOW_PCT
    if geo == "HI":
        return "derived", "Summed over the 51 House districts (counts: MOE root-sum-of-squares; rates: numerators ÷ universes)"
    if key == "snap_persons_est":
        return "derived", NOTE_PERSONS
    if key == "snap_gap_persons":
        return "derived", NOTE_GAP
    if key == "pct_snap_gap":
        return "derived", NOTE_GAP_PCT
    if key in ("pop_below_138fpl", "pct_below_138fpl"):
        return "derived", NOTE_138
    if key.startswith("pct_"):
        return "derived", "Count ÷ universe from the same table; MOE by the Census proportion formula"
    return "direct", None


def build() -> int:
    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    q = ",".join("?" * len(keys))
    c.execute(f"DELETE FROM observation WHERE indicator IN ({q})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({q})", keys)
    c.execute(f"DELETE FROM source WHERE source_id IN ({','.join('?' * (len(SOURCES) + 1))})", [*SOURCES, USDA])
    for sid, (t, title) in SOURCES.items():
        sha = hashlib.sha256(b"".join((RAW / f"{t}_{ch}_districts.json").read_bytes() for ch in ("house", "senate")))
        c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
                  (sid, "U.S. Census Bureau, American Community Survey", title, ACS_URL.format(t=t), None,
                   "Public domain (U.S. Government work)", sha.hexdigest()[:16]))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (USDA, "USDA Food and Nutrition Service", USDA_TITLE, USDA_URL, "2025-04",
               "Public domain (U.S. Government work)", hashlib.sha256(USDA_PDF.read_bytes()).hexdigest()[:16]))
    for k, (label, unit, topic, acs, _src) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, topic, acs))

    rows = []
    house, senate = district_values("house"), district_values("senate")
    add_low_end(house)
    add_low_end(senate)
    for chamber, prefix, vals in (("house", "HD", house), ("senate", "SD", senate)):
        for n, d in vals.items():
            for k, (v, m) in d.items():
                rows.append((f"{prefix}-{n:02d}", k, v, m))
    rows += [("HI", k, v, m) for k, (v, m) in state_values(house).items()]
    for geo, k, v, m in rows:
        method, note = _method(k, geo)
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"prog24-{geo}-{k}", geo, k, v, m, "FY 2022" if k in STATE_ONLY else VINTAGE, method, note,
                   INDICATORS[k][4]))
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: {len(INDICATORS)} program indicators, {len(rows)} observations")
    return len(rows)


if __name__ == "__main__":
    build()
