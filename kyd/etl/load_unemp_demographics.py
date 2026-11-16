"""Unemployment by sex, age, race/ethnicity and education (ACS 2020–2024 5-year) → kyd.sqlite table `breakdown`.

  python kyd/etl/load_unemp_demographics.py      (run after load_acs_profile.py)

Input: data/raw/census_bulk_2024/unemployment_demographics_{house_senate,counties_state}.csv, rebuilt by the
research agent (Optimus) from the keyless Census ACS summary-file tables B23025 (overall), B23001 (age × sex),
C23002A–I (race/ethnicity) and B23006 (education, ages 25–64); S2301 is not in the keyless files. See
data/raw/census_bulk_2024/MANIFEST_unemployment.md for formulas.

Rows keep the 90% MOE and the research file's quality_flag (`high_moe` = CV ≥ 30%, MOE ≥ rate, or MOE ≥ 5 pts).
Kalawao County (labor force ~49) is excluded. Each row gets an obs_id so agent answers can cite it and the
System-2 number check accepts its values.
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
RAW = REPO / "data" / "raw" / "census_bulk_2024"
SRC = "acs5_2024_unemployment_bc"
KEEP = {"overall", "sex", "age_collapsed", "race_ethnicity", "education", "age_by_sex_collapsed"}


def geo(gid: str) -> str | None:
    if gid == "0400000US15":
        return "HI"
    if gid.startswith("0500000US"):
        return None if gid.endswith("15005") else f"CNTY-{gid[-5:]}"
    if gid.startswith("620L900US15"):
        return f"HD-{int(gid[-3:]):02d}"
    if gid.startswith("610U900US15"):
        return f"SD-{int(gid[-3:]):02d}"
    return None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build() -> int:
    files = [RAW / "unemployment_demographics_house_senate.csv", RAW / "unemployment_demographics_counties_state.csv"]
    c = sqlite3.connect(DB)
    c.executescript("""
    DROP TABLE IF EXISTS breakdown;
    CREATE TABLE breakdown (obs_id TEXT PRIMARY KEY, geo_id TEXT, topic TEXT, dimension TEXT, grp TEXT, sex TEXT,
        value REAL, moe REAL, numerator REAL, numerator_moe REAL, denominator REAL, denominator_moe REAL,
        quality_flag TEXT, source_table TEXT, universe TEXT, notes TEXT, vintage TEXT, source_id TEXT);
    CREATE INDEX breakdown_geo ON breakdown(geo_id, topic);
    """)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "U.S. Census Bureau, American Community Survey (keyless summary-file tables; rates rebuilt)",
               "ACS 2020–2024 5-year B23025, B23001, C23002A–I, B23006: unemployment by sex, age, race/ethnicity, "
               "education — Hawaiʻi state, counties, 2022 House and Senate districts",
               "https://www.census.gov/programs-surveys/acs/data/summary-file.html", None,
               "Public domain (U.S. Government work)",
               hashlib.sha256(b"".join(f.read_bytes() for f in files)).hexdigest()[:16]))
    n, seen = 0, set()
    for f in files:
        for r in csv.DictReader(f.open(encoding="utf-8")):
            g = geo(r["geo_id"])
            if r["dimension"] == "age" and r["group"] in ("35 to 44 years", "45 to 54 years") and r["sex"] == "both":
                r = {**r, "dimension": "age_collapsed"}   # published groups that complete the collapsed age set
            if not g or r["dimension"] not in KEEP or r["quality_flag"] == "undefined_zero_clf":
                continue
            key = (g, r["dimension"], r["group"], r["sex"])
            if key in seen:
                continue
            seen.add(key)
            oid = "unemp24-" + hashlib.md5("|".join(key).encode()).hexdigest()[:12]
            c.execute("INSERT INTO breakdown VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (oid, g, "unemployment", r["dimension"], r["group"], r["sex"], _f(r["unemployment_rate_pct"]),
                       _f(r["unemployment_rate_moe_pct"]), _f(r["unemployed"]), _f(r["unemployed_moe"]),
                       _f(r["civilian_labor_force"]), _f(r["civilian_labor_force_moe"]), r["quality_flag"] or None,
                       r["source_table"], r["universe"], r["notes"] or None, "2020-2024", SRC))
            n += 1
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: unemployment breakdown, {n} rows")
    return n


if __name__ == "__main__":
    build()
