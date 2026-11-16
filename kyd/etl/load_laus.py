"""DBEDT/DLIR unemployment (LAUS) → district, county and state indicators in kyd.sqlite.

  python kyd/etl/load_laus.py      (run after load_acs_profile.py; needs kyd/data/tract_district_crosswalk.csv)

Input: data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-YYYY.xls (DBEDT Research & Economic Analysis
Division, Labor Research Branch). Each file gives annual-average employed, unemployed and labor force by 2020
census tract, plus county totals.

Important: DBEDT does not measure tracts directly. Its note: "The census share method is used to disaggregate
county data to census tract level, via the U.S. Census Bureau, 2020-2024 ACS 5-Year Estimates, and are applied to
current county data." So district figures here carry the CURRENT county LAUS level with the ACS tract pattern;
the county totals are the official LAUS figures.

District values: tract labor force and unemployed (rate × labor force, since small unemployed counts are shown
as "*") are allocated to districts with the population-weighted crosswalk, then rate = unemployed ÷ labor force.
County trend: county totals 2014–2025 (files before 2014 use a different layout).
"""
from __future__ import annotations
import csv
import hashlib
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

import xlrd

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
LABOR = REPO / "data" / "raw" / "dbedt.hawaii.gov" / "economic" / "labor"
XWALK = REPO / "kyd" / "data" / "tract_district_crosswalk.csv"
SRC = "dbedt_laus_tract"
LATEST = 2025
TREND_YEARS = range(2014, LATEST + 1)
COUNTY_FIPS = {"HONOLULU": "15003", "HAWAII": "15001", "KAUAI": "15007", "MAUI": "15009"}
INDICATORS = {
    "laus_unemp_rate": ("Unemployment rate, 2025 annual average (LAUS)", "pct"),
    "laus_labor_force": ("Civilian labor force, 2025 (LAUS)", "count"),
    "laus_unemployed": ("Unemployed, 2025 (LAUS)", "count"),
}
NOTE_DISTRICT = ("DBEDT tract estimates (county LAUS totals split to tracts by ACS 2020–2024 shares) allocated to "
                 "districts by 2020 population (kyd/data/tract_district_crosswalk.csv). Current county level, ACS pattern.")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _rows(year: int) -> list[list]:
    s = xlrd.open_workbook(str(LABOR / f"LFR_LAUS_CensusTract-{year}.xls")).sheet_by_index(0)
    return [s.row_values(i) for i in range(s.nrows)]


def county_totals(year: int) -> dict[str, dict[str, float]]:
    out = {}
    for r in _rows(year):
        txt = " ".join(str(x) for x in r).upper()
        m = re.search(r"\b(HONOLULU|HAWAII|KAUAI|MAUI) COUNTY TOTAL", txt)
        if m:
            nums = [_num(x) for x in r if _num(x) is not None]
            emp, unemp, lf, rate = nums[-4:]
            out[COUNTY_FIPS[m.group(1)]] = {"employed": emp, "unemployed": unemp, "labor_force": lf, "rate": rate}
    return out


def tracts(year: int) -> dict[str, dict[str, float]]:
    """2020 tract GEOID → labor force and unemployed (rate × LF)."""
    out, fips = {}, None
    for r in _rows(year):
        head = str(r[0]).upper()
        m = re.match(r"(HONOLULU|HAWAII|KAUAI|MAUI) COUNTY", head.strip())
        if m:
            fips = COUNTY_FIPS[m.group(1)]
            continue
        t, lf, rate = _num(r[1]), _num(r[5]), _num(r[6])
        if fips is None or t is None or lf is None or rate is None:
            continue
        whole, _, frac = f"{t:.2f}".partition(".")
        code = f"{int(whole):04d}{int(frac):02d}"
        out[f"{fips}{code}"] = {"labor_force": lf, "unemployed": rate * lf}
    return out


def build() -> int:
    xw = defaultdict(list)
    for r in csv.DictReader(XWALK.open()):
        xw[r["tract"]].append((r["geo_id"], float(r["weight"])))
    tr = tracts(LATEST)
    dist = defaultdict(lambda: {"labor_force": 0.0, "unemployed": 0.0})
    unmatched = 0.0
    for t, v in tr.items():
        if t not in xw:
            unmatched += v["labor_force"]
            continue
        for g, w in xw[t]:
            dist[g]["labor_force"] += v["labor_force"] * w
            dist[g]["unemployed"] += v["unemployed"] * w

    files = sorted(LABOR.glob("LFR_LAUS_CensusTract-*.xls"))
    c = sqlite3.connect(DB)
    keys = list(INDICATORS) + ["laus_unemp_rate_trend"]
    c.execute(f"DELETE FROM observation WHERE indicator IN ({','.join('?' * len(keys))}) OR indicator LIKE 'laus_unemp_rate_%'", keys)
    c.execute("DELETE FROM indicator WHERE indicator LIKE 'laus_%'")
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Hawaiʻi DBEDT Research & Economic Analysis Division (Labor Research Branch; DLIR LAUS)",
               "Civilian unemployment by census tract and county, annual averages 2014–2025",
               "https://dbedt.hawaii.gov/economic/labor/", "2026-06-04", "Public (State of Hawaiʻi)",
               hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()[:16]))
    for k, (label, unit) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, "employment", "LAUS"))
    for y in TREND_YEARS:
        if y != LATEST:
            c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)",
                      (f"laus_unemp_rate_{y}", f"Unemployment rate, {y} annual average (LAUS)", "pct", "employment_trend", "LAUS"))

    n = 0
    def put(geo, k, v, method, note, vintage=str(LATEST)):
        nonlocal n
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"laus-{geo}-{k}", geo, k, v, None, vintage, method, note, SRC))
        n += 1

    for g, v in dist.items():
        put(g, "laus_labor_force", round(v["labor_force"]), "derived", NOTE_DISTRICT)
        put(g, "laus_unemployed", round(v["unemployed"]), "derived", NOTE_DISTRICT)
        put(g, "laus_unemp_rate", round(100 * v["unemployed"] / v["labor_force"], 1), "derived", NOTE_DISTRICT)

    for y in TREND_YEARS:
        tots = county_totals(y)
        st = {k: sum(t[k] for t in tots.values()) for k in ("labor_force", "unemployed")}
        key = "laus_unemp_rate" if y == LATEST else f"laus_unemp_rate_{y}"
        for fips, t in tots.items():
            put(f"CNTY-{fips}", key, round(100 * t["rate"], 1), "direct", f"DBEDT county total, {y} annual average.", str(y))
            if y == LATEST:
                put(f"CNTY-{fips}", "laus_labor_force", t["labor_force"], "direct", "DBEDT county total.")
                put(f"CNTY-{fips}", "laus_unemployed", t["unemployed"], "direct", "DBEDT county total.")
        put("HI", key, round(100 * st["unemployed"] / st["labor_force"], 1), "derived",
            f"Sum of the four DBEDT county totals, {y}.", str(y))
        if y == LATEST:
            put("HI", "laus_labor_force", st["labor_force"], "derived", "Sum of the four DBEDT county totals.")
            put("HI", "laus_unemployed", st["unemployed"], "derived", "Sum of the four DBEDT county totals.")
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: LAUS {n} observations; {len(tr)} tracts, {len(dist)} districts; "
          f"{round(unmatched):,} labor force in tracts not in the crosswalk")
    return n


if __name__ == "__main__":
    build()
