"""HUD Picture of Subsidized Households 2025 (census-tract level) → district indicators in kyd.sqlite.

  python kyd/etl/load_hud.py        (run after load_acs_profile.py and build_tract_crosswalk.py)

Input: data/raw/hud/hi_tract_hud_2025.csv, the Hawaiʻi rows (state FIPS 15) of HUD's
TRACT_AK_MN_2025_2020census.xlsx (as of 31 Dec 2025, 2020 census tracts). Tract counts are allocated
to House and Senate districts with kyd/data/tract_district_crosswalk.csv (2020 population weights).

HUD codes: -1 = suppressed (small cell), -4 = not reported; both are treated as 0 for the sum, so district
totals are a floor. Units HUD could not place in a tract (tract code 999999 / county "Missing") are counted
in the state total only.
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
HUD = REPO / "data" / "raw" / "hud" / "hi_tract_hud_2025.csv"
XWALK = REPO / "kyd" / "data" / "tract_district_crosswalk.csv"
SRC = "hud_psh_2025_tract"
VINTAGE = "2025"

PROGRAMS = {  # indicator suffix → (program_label, sub_program)
    "total": ("Summary of All HUD Programs", "N/A"),
    "hcv": ("Housing Choice Vouchers", "N/A"),
    "public_housing": ("Public Housing", "N/A"),
    "pbs8": ("Project Based Section 8", "N/A"),
    "elderly_disabled": (("202/PRAC", "811/PRAC"), "N/A"),
}
INDICATORS = {
    "hud_units_total": ("HUD-subsidized units (all programs)", "count"),
    "hud_people_total": ("People in HUD-subsidized housing", "count"),
    "hud_units_hcv": ("Housing Choice Voucher (Section 8) households", "count"),
    "hud_units_public_housing": ("Public housing units", "count"),
    "hud_units_pbs8": ("Project-based Section 8 units", "count"),
    "hud_units_elderly_disabled": ("Elderly/disabled housing units (Section 202/811)", "count"),
    "hud_units_per_1k_hh": ("HUD-subsidized units per 1,000 households", "per_1000"),
}
NOTE = ("HUD tract counts allocated to districts by 2020 population share (kyd/data/tract_district_crosswalk.csv). "
        "Suppressed small cells count as 0, so this is a floor.")


def _n(v: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return x if x > 0 else 0.0


def build() -> int:
    rows = list(csv.DictReader(HUD.open(encoding="utf-8")))
    xw = defaultdict(list)
    for r in csv.DictReader(XWALK.open()):
        xw[r["tract"]].append((r["geo_id"], float(r["weight"])))

    tract: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    state: dict[str, float] = defaultdict(float)
    for r in rows:
        for key, (labels, sub) in PROGRAMS.items():
            labels = labels if isinstance(labels, tuple) else (labels,)
            if r["program_label"] in labels and r["sub_program"] == sub:
                tract[r["code"]][f"hud_units_{key}"] += _n(r["total_units"])
                state[f"hud_units_{key}"] += _n(r["total_units"])
                if key == "total":
                    tract[r["code"]]["hud_people_total"] += _n(r["people_total"])
                    state["hud_people_total"] += _n(r["people_total"])

    dist: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    unplaced = 0.0
    for t, vals in tract.items():
        if t not in xw:
            unplaced += vals.get("hud_units_total", 0)
            continue
        for geo, w in xw[t]:
            for k, v in vals.items():
                dist[geo][k] += v * w

    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    c.execute(f"DELETE FROM observation WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "U.S. Department of Housing and Urban Development (HUD)",
               "Picture of Subsidized Households 2025, census tracts (2020 geography), as of 31 Dec 2025",
               "https://www.huduser.gov/portal/datasets/assthsg.html", "2025-12-31", "Public domain (U.S. Government work)",
               hashlib.sha256(HUD.read_bytes()).hexdigest()[:16]))
    for k, (label, unit) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, "housing", "HUD PSH 2025"))
    hh = dict(c.execute("SELECT geo_id, value FROM observation WHERE indicator = 'households'"))

    n = 0
    def put(geo, k, v, method, note):
        nonlocal n
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"hud25-{geo}-{k}", geo, k, v, None, VINTAGE, method, note, SRC))
        n += 1

    for geo, vals in dist.items():
        for k in keys[:-1]:
            put(geo, k, round(vals.get(k, 0)), "derived", NOTE)
        if hh.get(geo):
            put(geo, "hud_units_per_1k_hh", round(1000 * vals.get("hud_units_total", 0) / hh[geo], 1), "derived",
                NOTE + " Households: ACS 2020–2024 (DP02_0001).")
    state_note = (f"Statewide HUD total, including {round(unplaced):,} units HUD could not place in a census tract "
                  "(not in any district figure). Suppressed cells count as 0.")
    for k in keys[:-1]:
        put("HI", k, round(state.get(k, 0)), "direct", state_note)
    if hh.get("HI"):
        put("HI", "hud_units_per_1k_hh", round(1000 * state["hud_units_total"] / hh["HI"], 1), "derived", state_note)
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: {len(INDICATORS)} HUD indicators, {n} observations; "
          f"{round(unplaced):,} units not placed in a tract (state total only)")
    return n


if __name__ == "__main__":
    build()
