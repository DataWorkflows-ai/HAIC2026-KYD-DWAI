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
    "acs5_2024_b22003_sld": ("B22003", "ACS 2020–2024 5-year B22003 SNAP by Poverty Status, Hawaiʻi State Legislative Districts"),
    "acs5_2024_b17024_sld": ("B17024", "ACS 2020–2024 5-year B17024 Age by Ratio of Income to Poverty, Hawaiʻi State Legislative Districts"),
    "acs5_2024_c27016_sld": ("C27016", "ACS 2020–2024 5-year C27016 Health Insurance by Age and Poverty, Hawaiʻi State Legislative Districts"),
    "acs5_2024_c27007_sld": ("C27007", "ACS 2020–2024 5-year C27007 Medicaid/Means-Tested Coverage by Age, Hawaiʻi State Legislative Districts"),
}
S1701, S2201 = "acs5_2024_s1701_sld", "acs5_2024_s2201_sld"
B22003, B17024 = "acs5_2024_b22003_sld", "acs5_2024_b17024_sld"
C27016, C27007 = "acs5_2024_c27016_sld", "acs5_2024_c27007_sld"
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
SNAP_GAP_RANGE_HI = (15_000, 46_000)                 # USDA rate CI plus eligible SE, rounded for demo wording
WIC_ELIGIBLE_CY2023 = (44_888, round(1.96 * 2_195))  # FNS EER CY2023 eligible people, 95% MOE
WIC_PARTICIPANTS_CY2023 = 25_712
WIC_PARTICIPANTS_AUG2026 = 25_804
WIC_REACH_CY2023 = 57.3
TANF_ACF_CHILDREN_FY2025 = 3_396
TANF_DHS_CHILDREN_SFY2025 = round(6_724 * 0.65)
ACT139_HIDOE_EXPECTED = 12_000

# key: label, unit, topic, acs line(s), source
INDICATORS = {
    "pop_below_200fpl": ("People below 200% of poverty", "count", "program", "S1701_C01_042", S1701),
    "pct_below_200fpl": ("People below 200% of poverty (SNAP income proxy)", "pct", "program", "S1701_C01_042/C01_001", S1701),
    "snap_hh_count": ("Households receiving SNAP", "count", "program", "S2201_C03_001", S2201),
    "snap_persons_est": ("People in SNAP households (est.)", "count", "program", "S2201_C03_001×DP02_0016", S2201),
    "snap_gap_persons": ("Loose SNAP income proxy: below 200% FPL minus estimated SNAP persons", "count", "program",
                         "S1701_C01_042−S2201_C03_001×DP02_0016", S2201),
    "pct_snap_gap": ("Loose SNAP income proxy share (not a participation gap)", "pct", "program",
                     "(S1701_C01_042−SNAP persons)/S1701_C01_042", S2201),
    "snap_poverty_hh_total": ("Poverty households in SNAP universe (ACS)", "count", "program", "B22003_E003+E006", B22003),
    "snap_poverty_hh_receiving": ("Poverty households reporting SNAP (ACS)", "count", "program", "B22003_E003", B22003),
    "snap_strict_gap_households": ("Poverty households not reporting SNAP (ACS strict gap)", "count", "program", "B22003_E006", B22003),
    "snap_poverty_hh_reach_rate": ("Poverty-household SNAP reach (ACS strict method)", "pct", "program",
                                   "B22003_E003/(E003+E006)", B22003),
    "children_below_fpl": ("Related children under 18 below poverty (context, not TANF eligibility)", "count", "program", "S1701_C02_005", S1701),
    "pct_children_below_fpl": ("Related children under 18 below poverty (context, not TANF eligibility)", "pct", "program",
                               "S1701_C02_005/C01_005", S1701),
    "tanf_deep_poverty_children": ("Children under 18 below 50% of poverty (TANF proxy)", "count", "program",
                                   "B17024_E003+E016+E029", B17024),
    "tanf_reach_low": ("TANF reach proxy, federal TANF children / children below 50% FPL", "pct", "program",
                       "ACF FY2025 children / B17024 below 50%", B17024),
    "tanf_reach_high": ("TANF reach proxy, DHS TANF+TAONF children / children below 50% FPL", "pct", "program",
                        "DHS SFY2025 clients × 65% under 18 / B17024 below 50%", B17024),
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
    "snap_gap_usda_low": ("SNAP eligible nonparticipants, low end of USDA range", "count", "program", "USDA FY2022 range", USDA),
    "snap_gap_usda_high": ("SNAP eligible nonparticipants, high end of USDA range", "count", "program", "USDA FY2022 range", USDA),
    "wic_eligible_est": ("WIC eligible people (CY2023 anchor, allocated estimate)", "count", "program", "FNS CY2023 × B17024 under-6 key", B17024),
    "wic_participating_est": ("WIC participants (Aug 2026 anchor, allocated estimate)", "count", "program", "FNS Aug 2026 × B17024 under-6 key", B17024),
    "wic_gap_est": ("WIC eligible people not served (allocated estimate)", "count", "program", "wic_eligible_est−wic_participating_est", B17024),
    "wic_reach_est": ("WIC reach (state rate applied to district)", "pct", "program", "FNS Aug 2026 / CY2023 eligible", B17024),
    "medquest_uninsured_eligible": ("Med-QUEST/CHIP uninsured-eligible people (ACS)", "count", "program",
                                    "C27016 uninsured under-65 below limits", C27016),
    "medquest_covered_acs": ("People with Medicaid/means-tested coverage (ACS)", "count", "program", "C27007 selected age rows", C27007),
    "medquest_reach_proxy": ("Med-QUEST reach proxy (mixed universe)", "pct", "program",
                             "C27007 covered / (covered + uninsured eligible)", C27007),
    "act139_acs_upper_children": ("Act 139 ACS upper-bound children in 185–299% band", "count", "program",
                                  "B17024 ages 6–17 at 185–299% poverty", B17024),
    "act139_hidoe_expected_children": ("Act 139 HIDOE expected additional students (state projection)", "count", "program",
                                       "HIDOE July 2026 release", B17024),
}
# Only the state has the USDA benchmark rows; districts get the allocated low end.
STATE_ONLY = ("snap_eligible_usda", "snap_participants_usda", "snap_participation_rate", "snap_participation_rate_ci_low",
              "snap_participation_rate_ci_high", "snap_participation_rate_us", "snap_gap_usda_low",
              "snap_gap_usda_high", "tanf_reach_low", "tanf_reach_high", "act139_hidoe_expected_children")
NOTE_138 = ("Linear interpolation between the 125% and 150% poverty-ratio counts (S1701 has no 138% line); "
            "MOE taken from the 150% line. Census poverty thresholds are national, not the higher Hawaiʻi guidelines "
            "Med-QUEST uses, so this likely understates the income-eligible pool.")
NOTE_PERSONS = ("SNAP households × district average household size (DP02_0016), as in scripts/snap_gap.py; "
                "MOE approximated from both MOEs. SNAP households are often larger than average, so this may understate.")
NOTE_GAP = ("People below 200% FPL minus estimated SNAP persons (scripts/snap_gap.py person-level gap). "
            "Loose context only: 200% is Hawaiʻi's BBCE gross screen, not the USDA eligible count, and this is not "
            "a participation gap. Use snap_strict_gap_households for district SNAP gap headlines. MOE root-sum-of-squares.")
NOTE_GAP_PCT = "snap_gap_persons ÷ pop_below_200fpl. Loose 200% income proxy, not a measured eligible-but-not-enrolled rate; MOE not computed."
NOTE_GAP_LOW = ("Low end of the SNAP gap range, grade C (allocated from a state figure). USDA estimates 161,104 Hawaiʻi "
                "residents eligible under federal rules and 130,188 eligible participants in FY 2022; the difference is "
                "shared among districts by their estimated SNAP persons. Assumes every district participates at the "
                "state rate, so it cannot show which districts lag. MOE not computed.")
NOTE_GAP_LOW_PCT = "snap_gap_low_persons ÷ pop_below_200fpl, the same denominator as the high end. MOE not computed."
NOTE_USDA = ("Transcribed from the USDA technical report (Cunnyngham 2025, Mathematica). Federal eligibility rules; "
             "monthly average for FY 2022.")
NOTE_SNAP_STRICT = ("ACS B22003 direct cell: poverty-status households not reporting SNAP in the past 12 months. "
                    "District-native survey estimate with 90% MOE; ACS under-reports SNAP and poverty households are "
                    "not the full Hawaiʻi BBCE eligible universe.")
NOTE_TANF = ("Proxy only, grade C: children under 18 below 50% of Census poverty. Hawaiʻi TANF's assistance standard "
             "is about 38% of poverty for a family of three; no official eligible count exists.")
NOTE_WIC = ("Allocated estimate, grade C by district: FNS CY2023 eligible people and Aug 2026 participants are shared "
            "to districts by ACS under-6 below-185% poverty. There is no public district or clinic caseload.")
NOTE_MEDQUEST = ("ACS eligible-uninsured construction: uninsured people under 65 below Medicaid/CHIP income bands. "
                 "The reach proxy mixes all-age Medicaid coverage with an under-65 uninsured gap, so use the gap count "
                 "as the solid figure and treat the rate as context.")
NOTE_ACT139 = ("ACS upper bound for children ages 6–17 in the 185–299% band. Act 139 uses Hawaiʻi HHS guidelines and "
               "department-school enrollment; HIDOE expects nearly 12,000 additional students statewide, so present "
               "statewide Act 139 as a range, not a point gap.")
NOTE_ACT139_HIDOE = ("HIDOE July 2026 projection of nearly 12,000 additional students statewide. Not an ACS count "
                     "and not allocated to districts.")


def _table(name: str, chamber: str) -> dict[int, dict]:
    header, rows = _load(RAW / f"{name}_{chamber}_districts.json")
    out = {}
    name_idx = header.index("NAME") if "NAME" in header else None
    geo_idx = header.index("GEO_ID") if "GEO_ID" in header else None
    for row in rows:
        n = _district_number(row[name_idx]) if name_idx is not None else int(str(row[geo_idx])[-3:]) if geo_idx is not None else None
        if n is not None:
            out[n] = {header[i]: row[i] for i in range(len(header))}
    return out


def _em(row: dict, col: str) -> tuple[float | None, float | None]:
    e_key, m_key = col + "E", col + "M"
    if e_key not in row:
        prefix, _, suffix = col.rpartition("_")
        e_key, m_key = f"{prefix}_E{suffix}", f"{prefix}_M{suffix}"
    return _num(row.get(e_key)), _num(row.get(m_key))


def _sum(row: dict, cols: list[str]) -> tuple[float, float]:
    vals = [_em(row, col) for col in cols]
    return sum(v or 0 for v, _ in vals), math.sqrt(sum((m or 0) ** 2 for _, m in vals))


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
    b22003, b17024 = _table("B22003", chamber), _table("B17024", chamber)
    c27016, c27007 = _table("C27016", chamber), _table("C27007", chamber)
    out = {}
    wic_key_total = sum(_sum(r, [f"B17024_{i:03d}" for i in range(3, 10)])[0] * 5 / 6 for r in b17024.values())
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
        if n in b22003:
            receiving = _em(b22003[n], "B22003_003")
            gap = _em(b22003[n], "B22003_006")
            total = ((receiving[0] or 0) + (gap[0] or 0), math.sqrt((receiving[1] or 0) ** 2 + (gap[1] or 0) ** 2))
            v["snap_poverty_hh_receiving"] = receiving
            v["snap_strict_gap_households"] = gap
            v["snap_poverty_hh_total"] = total
            v["snap_poverty_hh_reach_rate"] = _pct(receiving, total)
        if n in b17024:
            deep = _sum(b17024[n], ["B17024_003", "B17024_016", "B17024_029"])
            act139 = _sum(b17024[n], ["B17024_023", "B17024_024", "B17024_036", "B17024_037"])
            wic_key, wic_key_moe = _sum(b17024[n], [f"B17024_{i:03d}" for i in range(3, 10)])
            wic_key *= 5 / 6
            wic_key_moe *= 5 / 6
            wic_share = wic_key / wic_key_total if wic_key_total else 0
            v["tanf_deep_poverty_children"] = deep
            v["act139_acs_upper_children"] = act139
            v["wic_eligible_est"] = (round(WIC_ELIGIBLE_CY2023[0] * wic_share), round(WIC_ELIGIBLE_CY2023[1] * wic_share))
            v["wic_participating_est"] = (round(WIC_PARTICIPANTS_AUG2026 * wic_share), None)
            v["wic_gap_est"] = (v["wic_eligible_est"][0] - v["wic_participating_est"][0], v["wic_eligible_est"][1])
            v["wic_reach_est"] = (round(100 * WIC_PARTICIPANTS_AUG2026 / WIC_ELIGIBLE_CY2023[0], 1), None)
        if n in c27016:
            v["medquest_uninsured_eligible"] = _sum(c27016[n], ["C27016_005", "C27016_008", "C27016_015",
                                                               "C27016_018", "C27016_025"])
        if n in c27007:
            covered = _sum(c27007[n], ["C27007_004", "C27007_007", "C27007_010", "C27007_014",
                                       "C27007_017", "C27007_020"])
            v["medquest_covered_acs"] = covered
            gap = v.get("medquest_uninsured_eligible")
            if gap and covered[0] is not None:
                denom = (covered[0] or 0) + (gap[0] or 0)
                v["medquest_reach_proxy"] = (round(100 * covered[0] / denom, 1) if denom else None, None)
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
                               "snap_poverty_hh_total", "snap_poverty_hh_receiving", "snap_strict_gap_households",
                               "children_below_fpl", "tanf_deep_poverty_children", "adults_18_64_below_fpl",
                               "snap_hh_children", "snap_hh_60plus", "snap_hh_disability", "pop_below_125fpl",
                               "pop_below_150fpl", "pop_below_185fpl", "pop_below_138fpl", "wic_eligible_est",
                               "wic_participating_est", "wic_gap_est", "medquest_uninsured_eligible",
                               "medquest_covered_acs", "act139_acs_upper_children")}
    out["pct_below_138fpl"] = (_pct((out["pop_below_138fpl"][0], None), utot("S1701_C01_001"))[0], None)
    out["pct_below_200fpl"] = (_pct((out["pop_below_200fpl"][0], None), utot("S1701_C01_001"))[0], None)
    out["pct_children_below_fpl"] = (_pct((out["children_below_fpl"][0], None), utot("S1701_C01_005"))[0], None)
    out["pct_adults_18_64_below_fpl"] = (_pct((out["adults_18_64_below_fpl"][0], None), utot("S1701_C01_006"))[0], None)
    out["pct_snap_gap"] = (round(100 * out["snap_gap_persons"][0] / out["pop_below_200fpl"][0], 1), None)
    out["snap_poverty_hh_reach_rate"] = (_pct(out["snap_poverty_hh_receiving"], out["snap_poverty_hh_total"])[0], None)
    out["wic_reach_est"] = (round(100 * WIC_PARTICIPANTS_AUG2026 / WIC_ELIGIBLE_CY2023[0], 1), None)
    out["wic_eligible_est"] = WIC_ELIGIBLE_CY2023
    out["wic_participating_est"] = (WIC_PARTICIPANTS_AUG2026, None)
    out["wic_gap_est"] = (WIC_ELIGIBLE_CY2023[0] - WIC_PARTICIPANTS_AUG2026, WIC_ELIGIBLE_CY2023[1])
    mq_denom = out["medquest_covered_acs"][0] + out["medquest_uninsured_eligible"][0]
    out["medquest_reach_proxy"] = (round(100 * out["medquest_covered_acs"][0] / mq_denom, 1), None)
    out["snap_gap_low_persons"] = (SNAP_NOT_PARTICIPATING_HI, None)
    out["pct_snap_gap_low"] = (round(100 * SNAP_NOT_PARTICIPATING_HI / out["pop_below_200fpl"][0], 1), None)
    out["snap_eligible_usda"] = SNAP_ELIGIBLE_HI
    out["snap_participants_usda"] = (SNAP_PARTICIPANTS_HI, None)
    out["snap_participation_rate"] = (SNAP_RATE_HI, None)
    out["snap_participation_rate_ci_low"] = (SNAP_RATE_CI_HI[0], None)
    out["snap_participation_rate_ci_high"] = (SNAP_RATE_CI_HI[1], None)
    out["snap_participation_rate_us"] = (SNAP_RATE_US, None)
    out["snap_gap_usda_low"] = (SNAP_GAP_RANGE_HI[0], None)
    out["snap_gap_usda_high"] = (SNAP_GAP_RANGE_HI[1], None)
    out["tanf_reach_low"] = (round(100 * TANF_ACF_CHILDREN_FY2025 / out["tanf_deep_poverty_children"][0], 1), None)
    out["tanf_reach_high"] = (round(100 * TANF_DHS_CHILDREN_SFY2025 / out["tanf_deep_poverty_children"][0], 1), None)
    out["act139_hidoe_expected_children"] = (ACT139_HIDOE_EXPECTED, None)
    return {k: (round(v), round(m) if m else None) if INDICATORS[k][1] == "count" else (v, m) for k, (v, m) in out.items()}


def _vintage(key: str) -> str:
    if key in ("tanf_reach_low", "tanf_reach_high"):
        return "ACS 2020-2024 / ACF FY2025 / DHS SFY2025"
    if key == "act139_hidoe_expected_children":
        return "HIDOE July 2026"
    if key in STATE_ONLY:
        return "FY 2022"
    return VINTAGE


def _method(key: str, geo: str) -> tuple[str, str | None]:
    if key == "act139_hidoe_expected_children":
        return "derived", NOTE_ACT139_HIDOE
    if key in STATE_ONLY:
        if key.startswith("tanf_"):
            return "derived", NOTE_TANF
        if key.startswith("act139_"):
            return "derived", NOTE_ACT139
        return "direct", NOTE_USDA
    if key.startswith("snap_poverty_hh") or key == "snap_strict_gap_households":
        return "direct" if not key.endswith("_rate") else "derived", NOTE_SNAP_STRICT
    if key.startswith("tanf_"):
        return "derived", NOTE_TANF
    if key.startswith("wic_"):
        return "derived", NOTE_WIC
    if key.startswith("medquest_"):
        return "derived", NOTE_MEDQUEST
    if key.startswith("act139_"):
        return "derived", NOTE_ACT139
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
                  (f"prog24-{geo}-{k}", geo, k, v, m, _vintage(k), method, note,
                   INDICATORS[k][4]))
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: {len(INDICATORS)} program indicators, {len(rows)} observations")
    return len(rows)


if __name__ == "__main__":
    build()
