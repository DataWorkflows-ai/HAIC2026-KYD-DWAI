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
}
NOTE_PERSONS = ("SNAP households × district average household size (DP02_0016), as in scripts/snap_gap.py; "
                "MOE approximated from both MOEs. SNAP households are often larger than average, so this may understate.")
NOTE_GAP = ("People below 200% FPL minus estimated SNAP persons (scripts/snap_gap.py person-level gap). "
            "Proxy only: SNAP eligibility also depends on assets, household makeup and immigration status. "
            "MOE root-sum-of-squares.")
NOTE_GAP_PCT = "snap_gap_persons ÷ pop_below_200fpl. Proxy, not a measured eligible-but-not-enrolled rate; MOE not computed."


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


def state_values(house: dict[int, dict[str, tuple]]) -> dict[str, tuple]:
    def tot(k):
        xs = [d[k] for d in house.values() if k in d and d[k][0] is not None]
        return sum(x[0] for x in xs), math.sqrt(sum((x[1] or 0) ** 2 for x in xs))

    s1701 = _table("S1701", "house")
    def utot(col):
        return sum(_num(r.get(col + "E")) or 0 for r in s1701.values()), None

    out = {k: tot(k) for k in ("pop_below_200fpl", "snap_hh_count", "snap_persons_est", "snap_gap_persons",
                               "children_below_fpl", "adults_18_64_below_fpl")}
    out["pct_below_200fpl"] = (_pct((out["pop_below_200fpl"][0], None), utot("S1701_C01_001"))[0], None)
    out["pct_children_below_fpl"] = (_pct((out["children_below_fpl"][0], None), utot("S1701_C01_005"))[0], None)
    out["pct_adults_18_64_below_fpl"] = (_pct((out["adults_18_64_below_fpl"][0], None), utot("S1701_C01_006"))[0], None)
    out["pct_snap_gap"] = (round(100 * out["snap_gap_persons"][0] / out["pop_below_200fpl"][0], 1), None)
    return {k: (round(v), round(m) if m else None) if INDICATORS[k][1] == "count" else (v, m) for k, (v, m) in out.items()}


def _method(key: str, geo: str) -> tuple[str, str | None]:
    if geo == "HI":
        return "derived", "Summed over the 51 House districts (counts: MOE root-sum-of-squares; rates: numerators ÷ universes)"
    if key == "snap_persons_est":
        return "derived", NOTE_PERSONS
    if key == "snap_gap_persons":
        return "derived", NOTE_GAP
    if key == "pct_snap_gap":
        return "derived", NOTE_GAP_PCT
    if key.startswith("pct_"):
        return "derived", "Count ÷ universe from the same table; MOE by the Census proportion formula"
    return "direct", None


def build() -> int:
    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    q = ",".join("?" * len(keys))
    c.execute(f"DELETE FROM observation WHERE indicator IN ({q})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({q})", keys)
    c.execute(f"DELETE FROM source WHERE source_id IN ({','.join('?' * len(SOURCES))})", list(SOURCES))
    for sid, (t, title) in SOURCES.items():
        sha = hashlib.sha256(b"".join((RAW / f"{t}_{ch}_districts.json").read_bytes() for ch in ("house", "senate")))
        c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
                  (sid, "U.S. Census Bureau, American Community Survey", title, ACS_URL.format(t=t), None,
                   "Public domain (U.S. Government work)", sha.hexdigest()[:16]))
    for k, (label, unit, topic, acs, _src) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, topic, acs))

    rows = []
    house = district_values("house")
    for chamber, prefix, vals in (("house", "HD", house), ("senate", "SD", district_values("senate"))):
        for n, d in vals.items():
            for k, (v, m) in d.items():
                rows.append((f"{prefix}-{n:02d}", k, v, m))
    rows += [("HI", k, v, m) for k, (v, m) in state_values(house).items()]
    for geo, k, v, m in rows:
        method, note = _method(k, geo)
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"prog24-{geo}-{k}", geo, k, v, m, VINTAGE, method, note, INDICATORS[k][4]))
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: {len(INDICATORS)} program indicators, {len(rows)} observations")
    return len(rows)


if __name__ == "__main__":
    build()
