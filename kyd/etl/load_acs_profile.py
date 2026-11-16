"""ACS 2020–2024 5-year Data Profiles (DP02–DP05) by legislative district → kyd/data/kyd.sqlite.

Input: data/raw/acs2024_5yr_{house,senate}_hi.xlsx. These are the Hawaii State Data
Center (DBEDT) tabulations of the Census Bureau profiles for the 2022-plan districts.

  python kyd/etl/load_acs_profile.py

Each indicator is located by (sheet, section header, row label, anchor). The
anchor is a preceding label that disambiguates repeated labels. For example,
"65 years and over" appears in several places, and the anchor "All people"
selects the one under the poverty table.

State values are DERIVED by summing the 51 House districts, which partition the
state:
  - counts: summed estimate; MOE is the root-sum-of-squares approximation
  - percents: summed numerators over summed implied universes; MOE not computed
  - medians: cannot be derived and are left empty
Every derived value is flagged method='derived' with a note.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
DB = REPO / "kyd" / "data" / "kyd.sqlite"
COUNTIES = json.loads((REPO / "kyd" / "data" / "district_counties.json").read_text())
COUNTY_NAME = {"Hawaii": "Hawaiʻi County", "Maui": "Maui County", "Kauai": "Kauaʻi County",
               "Oahu": "City & County of Honolulu", "Honolulu": "City & County of Honolulu"}

# key, label shown, unit, topic, sheet, section, row label, field(est|pct), anchor, ACS line
INDICATORS = [
    ("total_pop", "Total population", "count", "population", "DP05", "SEX AND AGE", "Total population", "est", None, "DP05_0001"),
    ("median_age", "Median age", "years", "age", "DP05", "SEX AND AGE", "Median age (years)", "est", None, "DP05_0018"),
    ("pct_under5", "Under 5 years", "pct", "age", "DP05", "SEX AND AGE", "Under 5 years", "pct", None, "DP05_0005"),
    ("pct_under18", "Under 18 years", "pct", "age", "DP05", "SEX AND AGE", "Under 18 years", "pct", None, "DP05_0019"),
    ("pct_65plus", "65 years and over", "pct", "age", "DP05", "SEX AND AGE", "65 years and over", "pct", "62 years and over", "DP05_0024"),
    ("households", "Total households", "count", "households", "DP02", "HOUSEHOLDS BY TYPE", "Total households", "est", None, "DP02_0001"),
    ("avg_hh_size", "Average household size", "persons", "households", "DP02", "HOUSEHOLDS BY TYPE", "Average household size", "est", None, "DP02_0016"),
    ("pct_bachelors_plus", "Bachelor's degree or higher (25+)", "pct", "education", "DP02", "EDUCATIONAL ATTAINMENT", "Bachelor's degree or higher", "pct", None, "DP02_0068"),
    ("pct_veterans", "Civilian veterans (18+)", "pct", "population", "DP02", "VETERAN STATUS", "Civilian veterans", "pct", None, "DP02_0070"),
    ("pct_disability", "With a disability", "pct", "health", "DP02", "DISABILITY STATUS OF THE CIVILIAN NONINSTITUTIONALIZED POPULATION", "With a disability", "pct", None, "DP02_0072"),
    ("pct_foreign_born", "Foreign born", "pct", "population", "DP02", "PLACE OF BIRTH", "Foreign-born", "pct", None, "DP02_0094"),
    ("pct_limited_english", 'Speak English less than "very well" (5+)', "pct", "language", "DP02", "LANGUAGE SPOKEN AT HOME", 'Speak English less than "very well"', "pct", None, "DP02_0115"),
    ("pct_broadband", "Households with broadband", "pct", "connectivity", "DP02", "COMPUTERS AND INTERNET USE", "With a broadband Internet subscription", "pct", None, "DP02_0154"),
    ("unemployment_rate", "Unemployment rate", "pct", "employment", "DP03", "EMPLOYMENT STATUS", "Unemployment Rate", "pct", None, "DP03_0009"),
    ("median_hh_income", "Median household income", "usd", "income", "DP03", "INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)", "Median household income (dollars)", "est", None, "DP03_0062"),
    ("per_capita_income", "Per capita income", "usd", "income", "DP03", "INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)", "Per capita income (dollars)", "est", None, "DP03_0088"),
    ("pct_ssi_hh", "Households with SSI", "pct", "assistance", "DP03", "INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)", "With Supplemental Security Income", "pct", None, "DP03_0070"),
    ("pct_cash_assist_hh", "Households with cash public assistance", "pct", "assistance", "DP03", "INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)", "With cash public assistance income", "pct", None, "DP03_0072"),
    ("pct_snap_hh", "Households receiving SNAP", "pct", "assistance", "DP03", "INCOME AND BENEFITS (IN 2024 INFLATION-ADJUSTED DOLLARS)", "With Food Stamp/SNAP benefits in the past 12 months", "pct", None, "DP03_0074"),
    ("pct_uninsured", "Without health insurance", "pct", "health", "DP03", "HEALTH INSURANCE COVERAGE", "No health insurance coverage", "pct", None, "DP03_0099"),
    ("pct_below_fpl", "People below poverty level", "pct", "income", "DP03", "PERCENTAGE OF FAMILIES AND PEOPLE WHOSE INCOME IN THE PAST 12 MONTHS IS BELOW THE POVERTY LEVEL", "All people", "pct", None, "DP03_0128"),
    ("pct_child_poverty", "Children (<18) below poverty level", "pct", "income", "DP03", "PERCENTAGE OF FAMILIES AND PEOPLE WHOSE INCOME IN THE PAST 12 MONTHS IS BELOW THE POVERTY LEVEL", "Under 18 years", "pct", "All people", "DP03_0129"),
    ("pct_65plus_poverty", "Seniors (65+) below poverty level", "pct", "income", "DP03", "PERCENTAGE OF FAMILIES AND PEOPLE WHOSE INCOME IN THE PAST 12 MONTHS IS BELOW THE POVERTY LEVEL", "65 years and over", "pct", "All people", "DP03_0135"),
    ("pct_renter", "Renter-occupied homes", "pct", "housing", "DP04", "HOUSING TENURE", "Renter-occupied", "pct", None, "DP04_0047"),
    ("pct_no_vehicle", "Households with no vehicle", "pct", "housing", "DP04", "VEHICLES AVAILABLE", "No vehicles available", "pct", None, "DP04_0058"),
    ("median_home_value", "Median home value", "usd", "housing", "DP04", "VALUE", "Median (dollars)", "est", None, "DP04_0089"),
    ("median_gross_rent", "Median gross rent", "usd", "housing", "DP04", "GROSS RENT", "Median (dollars)", "est", None, "DP04_0134"),
    ("_rent_30_35", "", "pct", "", "DP04", "GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME (GRAPI)", "30.0 to 34.9 percent", "pct", None, "DP04_0141"),
    ("_rent_35_plus", "", "pct", "", "DP04", "GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME (GRAPI)", "35.0 percent or more", "pct", None, "DP04_0142"),
]
DERIVED_RENT = ("pct_rent_burden_30", "Renters paying 30%+ of income on rent", "pct", "housing")

SOURCE = {
    "source_id": "acs5_2024_dp_sld",
    "publisher": "U.S. Census Bureau, American Community Survey (tabulated by Hawaiʻi State Data Center, DBEDT)",
    "title": "ACS 2020–2024 5-year Data Profiles DP02–DP05, Hawaiʻi State Legislative Districts (2022 plan)",
    "url": "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/",
    "release_date": None, "license": "Public domain (U.S. Government work)",
}
VINTAGE = "2020-2024"


def num(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("±", "").replace("%", "").replace("+", "")
    if s in ("", "(X)", "N", "-", "**", "***", "*****", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse(path: Path, chamber: str) -> dict[str, dict[str, tuple]]:
    """→ {geo_id: {key: (value, moe, est, est_moe)}}"""
    wb = openpyxl.load_workbook(path, read_only=True)
    out: dict[str, dict[str, tuple]] = {}
    for sheet in ("DP02", "DP03", "DP04", "DP05"):
        rows = list(wb[sheet].iter_rows(values_only=True))
        header = rows[0]
        cols = []                                  # (geo_id, est_col)
        for i, h in enumerate(header):
            m = re.search(r"(House|Senate) District (\d+)", str(h or ""))
            if m:
                cols.append((("HD" if chamber == "house" else "SD") + f"-{int(m.group(2)):02d}", i))
        want = [x for x in INDICATORS if x[4] == sheet]
        section, anchor_seen, found = None, set(), set()
        for r in rows[2:]:
            label = (r[0] or "").strip() if isinstance(r[0], str) else r[0]
            if label and all(v is None for v in r[1:5]):
                section, anchor_seen = label, set()
                continue
            for key, _, _, _, _, sec, lab, field, anchor, _ in want:
                if key in found or sec != section or lab != label or (anchor and anchor not in anchor_seen):
                    continue
                found.add(key)
                for gid, c in cols:
                    est, est_moe, pct, pct_moe = (num(r[c]), num(r[c + 1]), num(r[c + 2]), num(r[c + 3]))
                    v, m = (est, est_moe) if field == "est" else (pct, pct_moe)
                    out.setdefault(gid, {})[key] = (v, m, est, est_moe)
            if label:
                anchor_seen.add(label)
        missing = {x[0] for x in want} - found
        assert not missing, f"{path.name} {sheet}: not found {missing}"
    return out


def build() -> None:
    house = parse(RAW / "acs2024_5yr_house_hi.xlsx", "house")
    senate = parse(RAW / "acs2024_5yr_senate_hi.xlsx", "senate")
    assert len(house) == 51 and len(senate) == 25, (len(house), len(senate))
    data = {**house, **senate}

    for gid, d in data.items():                       # derived rent burden
        a, b = d["_rent_30_35"], d["_rent_35_plus"]
        if a[0] is not None and b[0] is not None:
            moe = math.sqrt((a[1] or 0) ** 2 + (b[1] or 0) ** 2)
            d["pct_rent_burden_30"] = (round(a[0] + b[0], 1), round(moe, 1), (a[2] or 0) + (b[2] or 0), None)

    state = {}                                        # derived state totals from House districts
    inds = [x for x in INDICATORS if not x[0].startswith("_")] + [(*DERIVED_RENT, None, None, None, "pct", None, None)]
    for key, _, unit, *_rest in inds:
        field = _rest[4] if len(_rest) > 4 else "pct"
        vals = [house[g].get(key) for g in house]
        if any(v is None or v[2] is None for v in vals):
            continue
        if unit == "count":
            state[key] = (sum(v[0] for v in vals), round(math.sqrt(sum((v[1] or 0) ** 2 for v in vals))), "sum of 51 House districts; MOE by root-sum-of-squares")
        elif unit == "pct":
            num_, den = 0.0, 0.0
            for v in vals:
                if v[0] and v[0] > 0:
                    num_ += v[2]
                    den += v[2] / (v[0] / 100)
            if den:
                state[key] = (round(100 * num_ / den, 1), None, "numerators ÷ implied universes summed over 51 House districts; MOE not computed")

    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE geography (geo_id TEXT PRIMARY KEY, geo_type TEXT, name TEXT, counties TEXT);
    CREATE TABLE indicator (indicator TEXT PRIMARY KEY, label TEXT, unit TEXT, topic TEXT, acs TEXT);
    CREATE TABLE source (source_id TEXT PRIMARY KEY, publisher TEXT, title TEXT, url TEXT, release_date TEXT, license TEXT, checksum TEXT);
    CREATE TABLE observation (obs_id TEXT PRIMARY KEY, geo_id TEXT, indicator TEXT, value REAL, moe REAL,
        vintage TEXT, method TEXT, method_note TEXT, source_id TEXT);
    CREATE INDEX obs_geo ON observation(geo_id, indicator);
    """)
    sha = hashlib.sha256((RAW / "acs2024_5yr_house_hi.xlsx").read_bytes() + (RAW / "acs2024_5yr_senate_hi.xlsx").read_bytes()).hexdigest()
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)", (*SOURCE.values(), sha[:16]))
    c.execute("INSERT INTO geography VALUES ('HI','state','State of Hawaiʻi','[]')")
    for gid in sorted(data):
        t, n = ("sldl", "House") if gid.startswith("HD") else ("sldu", "Senate")
        c.execute("INSERT INTO geography VALUES (?,?,?,?)",
                  (gid, t, f"{n} District {int(gid[3:])}", json.dumps([COUNTY_NAME.get(COUNTIES.get(gid, ""), "")])))
    for key, label, unit, topic, *_r in inds:
        acs = _r[-1] if _r and _r[-1] else "DP04_0141+DP04_0142"
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (key, label, unit, topic, acs))
    keys = {x[0] for x in inds}
    for gid, d in data.items():
        for key, v in d.items():
            if key in keys:
                c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                          (f"acs24-{gid}-{key}", gid, key, v[0], v[1], VINTAGE,
                           "derived" if key == "pct_rent_burden_30" else "direct",
                           "Sum of GRAPI 30.0–34.9% and 35.0%+ bands; MOE by root-sum-of-squares" if key == "pct_rent_burden_30" else None,
                           SOURCE["source_id"]))
    for key, (v, m, note) in state.items():
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"acs24-HI-{key}", "HI", key, v, m, VINTAGE, "derived", note, SOURCE["source_id"]))
    c.commit()
    n = c.execute("select count(*) from observation").fetchone()[0]
    print(f"{DB.relative_to(REPO)}: {len(data)} districts, {len(inds)} indicators, {n} observations, state values for {len(state)}")


if __name__ == "__main__":
    build()
    import load_programs  # program-analysis indicators live in the same database; rebuild them too
    load_programs.build()
    import load_hud       # HUD subsidized housing by district (needs kyd/data/tract_district_crosswalk.csv)
    load_hud.build()
    import load_school_meals  # HCNP free/reduced meals by district (research rollup, charters excluded)
    load_school_meals.build()
    import load_laus          # DBEDT LAUS unemployment 2025 by district/county + 2014–2025 county trend
    load_laus.build()
    import load_unemp_demographics  # ACS unemployment by sex/age/race/education (breakdown table)
    load_unemp_demographics.build()
