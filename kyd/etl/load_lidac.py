"""Share of residents in LIDAC block groups, by district → kyd.sqlite.

  python kyd/etl/load_lidac.py     (run after load_acs_profile.py; needs kyd/data/bg_district_crosswalk.csv)

LIDAC = Low-Income and Disadvantaged Communities (Hawaiʻi Climate Action Plan screening, March 2026; Hawaiʻi
Statewide GIS Program layer HumanHealthSafety/MapServer/22). It flags 2020 Census block groups: `unified_lidac`
0 = not LIDAC, 1 = LIDAC (baseline), 2 = most vulnerable LIDAC (data/raw/gis/lidac_bg_flags.csv; method in
data/raw/gis/lidac_metadata.txt).

Each block group's 2020 population is split across districts by area (kyd/data/bg_district_crosswalk.csv, the
same weights as the tract crosswalk). District share = LIDAC population ÷ total population, both 2020.
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
FLAGS = REPO / "data" / "raw" / "gis" / "lidac_bg_flags.csv"
XWALK = REPO / "kyd" / "data" / "bg_district_crosswalk.csv"
SRC = "hi_gis_lidac_2026"
INDICATORS = {
    "pct_pop_lidac": ("Residents in LIDAC block groups (low-income & disadvantaged)", "pct"),
    "pct_pop_lidac_most": ("Residents in most-vulnerable LIDAC block groups", "pct"),
    "pop_lidac": ("Residents in LIDAC block groups (2020 population)", "count"),
}
NOTE = ("2020 block-group population split across districts by area (kyd/data/bg_district_crosswalk.csv); "
        "LIDAC flag from the Hawaiʻi CAP LIDAC layer (unified_lidac 1 or 2; most vulnerable = 2).")


def build() -> int:
    flag = {r["bg_geoid"]: int(r["unified_lidac"]) for r in csv.DictReader(FLAGS.open(encoding="utf-8"))}
    tot, lid, most = defaultdict(float), defaultdict(float), defaultdict(float)
    for r in csv.DictReader(XWALK.open()):
        p, f, g = float(r["pop20_allocated"]), flag.get(r["bg"], 0), r["geo_id"]
        tot[g] += p
        lid[g] += p if f >= 1 else 0
        most[g] += p if f == 2 else 0
        if r["chamber"] == "house":
            tot["HI"] += p
            lid["HI"] += p if f >= 1 else 0
            most["HI"] += p if f == 2 else 0
    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    q = ",".join("?" * len(keys))
    c.execute(f"DELETE FROM observation WHERE indicator IN ({q})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({q})", keys)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Hawaiʻi Statewide GIS Program / Hawaiʻi Climate Change Mitigation & Adaptation Commission",
               "Low Income and Disadvantaged Communities (LIDAC) – 2026, 2020 Census block groups",
               "https://geodata.hawaii.gov/arcgis/rest/services/HumanHealthSafety/MapServer/22", "2026-03-19",
               "Public (State of Hawaiʻi Terms of Use)", hashlib.sha256(FLAGS.read_bytes()).hexdigest()[:16]))
    for k, (label, unit) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, "equity", "LIDAC 2026 × 2020 BG pop"))
    n = 0
    for g in tot:
        if not tot[g]:
            continue
        for k, v in (("pct_pop_lidac", round(100 * lid[g] / tot[g], 1)),
                     ("pct_pop_lidac_most", round(100 * most[g] / tot[g], 1)), ("pop_lidac", round(lid[g]))):
            c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                      (f"lidac26-{g}-{k}", g, k, v, None, "2026 (2020 population)", "derived",
                       NOTE if g != "HI" else "Statewide: " + NOTE, SRC))
            n += 1
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: LIDAC {n} observations; state {round(100 * lid['HI'] / tot['HI'], 1)}% of residents "
          f"in LIDAC block groups ({round(100 * most['HI'] / tot['HI'], 1)}% most vulnerable)")
    return n


if __name__ == "__main__":
    build()
