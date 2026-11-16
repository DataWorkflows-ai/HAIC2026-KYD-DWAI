"""Official ACS 2020–2024 5-year Data Profile values for the State of Hawaiʻi and its counties → kyd.sqlite.

  python kyd/etl/load_acs_state_county.py     (chained from load_acs_profile.py)

Inputs: data/raw/census.hawaii.gov/acs/acs2024_5yr_{state,counties}_hi.xlsx (Hawaiʻi State Data Center tabulations
of DP02–DP05, the same layout as the legislative-district workbooks). These are the published state and county
estimates, so medians and rates come straight from the Census Bureau instead of being rebuilt from districts.
They replace the earlier district-summed state values and add county rows (CNTY-15001 Hawaiʻi, 15003 Honolulu,
15007 Kauaʻi, 15009 Maui) used for the county comparison column.
"""
from __future__ import annotations
import hashlib
import math
import re
import sqlite3
from pathlib import Path

import openpyxl

from load_acs_profile import INDICATORS, DERIVED_RENT, VINTAGE, num

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
ACS = REPO / "data" / "raw" / "census.hawaii.gov" / "acs"
FILES = [ACS / "acs2024_5yr_state_hi.xlsx", ACS / "acs2024_5yr_counties_hi.xlsx"]
GEO = {"Hawaii": "HI", "Hawaii County, Hawaii": "CNTY-15001", "Honolulu County, Hawaii": "CNTY-15003",
       "Kauai County, Hawaii": "CNTY-15007", "Maui County, Hawaii": "CNTY-15009"}   # Kalawao (15005) is not used
SRC = "acs5_2024_dp_state_county"


def parse(path: Path) -> dict[str, dict[str, tuple]]:
    wb = openpyxl.load_workbook(path, read_only=True)
    out: dict[str, dict[str, tuple]] = {}
    for sheet in ("DP02", "DP03", "DP04", "DP05"):
        rows = list(wb[sheet].iter_rows(values_only=True))
        cols = [(GEO[str(h).strip()], i) for i, h in enumerate(rows[0]) if h and str(h).strip() in GEO]
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
                    out.setdefault(gid, {})[key] = (est, est_moe) if field == "est" else (pct, pct_moe)
            if label:
                anchor_seen.add(label)
        missing = {x[0] for x in want} - found
        assert not missing, f"{path.name} {sheet}: not found {missing}"
    return out


def build() -> int:
    data: dict[str, dict[str, tuple]] = {}
    for f in FILES:
        data.update(parse(f))
    assert set(data) == set(GEO.values()), set(data)
    for d in data.values():
        a, b = d.pop("_rent_30_35"), d.pop("_rent_35_plus")
        if a[0] is not None and b[0] is not None:
            d[DERIVED_RENT[0]] = (round(a[0] + b[0], 1), round(math.sqrt((a[1] or 0) ** 2 + (b[1] or 0) ** 2), 1))
    c = sqlite3.connect(DB)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    sha = hashlib.sha256(b"".join(f.read_bytes() for f in FILES)).hexdigest()[:16]
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "U.S. Census Bureau, American Community Survey (tabulated by Hawaiʻi State Data Center, DBEDT)",
               "ACS 2020–2024 5-year Data Profiles DP02–DP05, State of Hawaiʻi and counties",
               "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/", None, "Public domain (U.S. Government work)", sha))
    n = 0
    for gid, d in data.items():
        for key, (v, m) in d.items():
            if v is None:
                continue
            c.execute("DELETE FROM observation WHERE geo_id = ? AND indicator = ?", (gid, key))
            c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                      (f"acs24-{gid}-{key}", gid, key, v, m, VINTAGE,
                       "derived" if key == DERIVED_RENT[0] else "direct",
                       "Sum of GRAPI 30.0–34.9% and 35.0%+ bands; MOE by root-sum-of-squares" if key == DERIVED_RENT[0] else None,
                       SRC))
            n += 1
    c.commit()
    hi = dict(c.execute("SELECT indicator, value FROM observation WHERE geo_id='HI' AND indicator IN "
                        "('median_hh_income','pct_below_fpl','unemployment_rate')").fetchall())
    c.close()
    print(f"{DB.relative_to(REPO)}: state + 4 counties, {n} official ACS profile observations; state {hi}")
    return n


if __name__ == "__main__":
    build()
