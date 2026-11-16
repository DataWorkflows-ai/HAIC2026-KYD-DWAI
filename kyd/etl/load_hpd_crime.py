"""Oʻahu crime by legislative district (ESTIMATE) from HPD annual reports → kyd.sqlite.

  python kyd/etl/load_hpd_crime.py        (run after load_acs_profile.py)

Input (research agent Optimus, 2026-11-16; method in data/raw/hpd_crime/BEAT_GIS_METHOD.md, EXTRACTION_NOTES.md):
  crime_by_legislative_district_ESTIMATE.csv  HPD beat offense counts (own-year annual report, 2017–2025) × beat→district
                                              shares; weight `pop_share_or_area_if_pop_lt50` (2020 block population,
                                              area for beats with < 50 residents)
  hpd_index_citywide_by_year.csv              HPD Table 1 (UCR/SRS) citywide index offenses — the official totals

Status: ESTIMATE / APPROXIMATE. HPD publishes no beat GIS; beat polygons were traced from the 2025 report maps
(map data Google), ~50–150 m error in town. Beat counts are raw case counts and run ~7–17% above Table 1. Crime is
assumed spread within a beat by residents, which is weak for Waikīkī, Ala Moana and airport beats. Not to be mixed
with the Attorney General's NIBRS dashboard. Credit: "HPD Annual Reports; beat geometry traced from HPD 2025 report
maps (map data Google)".
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
RAW = REPO / "data" / "raw" / "hpd_crime"
SRC = "hpd_annual_reports_beats_est"
WEIGHT = "pop_share_or_area_if_pop_lt50"
LATEST = 2025
CREDIT = "HPD Annual Reports; beat geometry traced from HPD 2025 report maps (map data Google)"
NOTE = ("ESTIMATE: HPD beat counts × APPROXIMATE beat→district shares (2020 population). " + CREDIT +
        ". Raw case counts run ~7–17% above HPD's official Table 1.")
INDICATORS = {
    "crime_total_est": ("Index offenses, 2025 (ESTIMATE, Oʻahu)", "count", "crime"),
    "crime_violent_est": ("Violent offenses, 2025 (ESTIMATE, Oʻahu)", "count", "crime"),
    "crime_property_est": ("Property offenses, 2025 (ESTIMATE, Oʻahu)", "count", "crime"),
    "crime_rate_per_1k_est": ("Index offenses per 1,000 residents, 2025 (ESTIMATE, Oʻahu)", "per_1000", "crime"),
    "crime_violent_per_1k_est": ("Violent offenses per 1,000 residents, 2025 (ESTIMATE, Oʻahu)", "per_1000", "crime"),
}
OFF = {"total": "crime_total_est", "violent_total": "crime_violent_est", "property_total": "crime_property_est"}


def build() -> int:
    est = RAW / "crime_by_legislative_district_ESTIMATE.csv"
    tbl = RAW / "hpd_index_citywide_by_year.csv"
    vals = defaultdict(dict)   # (geo, year) → {indicator: value}
    for r in csv.DictReader(est.open(encoding="utf-8")):
        if r["weight"] != WEIGHT or r["layer"] not in ("house", "senate") or r["offense"] not in OFF:
            continue
        g = f"{'HD' if r['layer'] == 'house' else 'SD'}-{int(r['leg_district']):02d}"
        vals[(g, int(r["year"]))][OFF[r["offense"]]] = float(r["estimated_count"])
    official = {}
    for r in csv.DictReader(tbl.open(encoding="utf-8")):
        if r["is_own_year_report"] == "True" and r["offense"] in ("index_total", "violent_crime_total", "property_crime_total"):
            official[(int(float(r["data_year"])), r["offense"])] = float(r["count"])

    c = sqlite3.connect(DB)
    pop = dict(c.execute("SELECT geo_id, value FROM observation WHERE indicator = 'total_pop'"))
    c.execute("DELETE FROM observation WHERE source_id = ?", (SRC,))
    c.execute("DELETE FROM indicator WHERE indicator LIKE 'crime_%'")
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Honolulu Police Department (annual reports); beat→district shares by research agent (ESTIMATE)",
               "HPD Annual Reports 2017–2025: index offenses by beat, allocated to 2022 legislative districts. " + CREDIT,
               "https://www.honolulupd.org/information/annual-report/", "2026", "Public records, City & County of Honolulu",
               hashlib.sha256(est.read_bytes() + tbl.read_bytes()).hexdigest()[:16]))
    for k, (label, unit, topic) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, topic, "HPD annual reports"))
    years = sorted({y for _, y in vals})
    for y in years:
        if y != LATEST:
            c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (f"crime_total_est_{y}", f"Index offenses, {y} (ESTIMATE, Oʻahu)",
                                                                  "count", "crime_trend", "HPD annual reports"))
    n = 0
    def put(geo, k, v, note=NOTE, vintage=str(LATEST), method="derived"):
        nonlocal n
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"hpd-{geo}-{k}", geo, k, v, None, vintage, method, note, SRC))
        n += 1
    for (g, y), v in vals.items():
        if y == LATEST:
            for k in ("crime_total_est", "crime_violent_est", "crime_property_est"):
                put(g, k, round(v[k]))
            if pop.get(g):
                put(g, "crime_rate_per_1k_est", round(1000 * v["crime_total_est"] / pop[g], 1),
                    NOTE + " Residents: ACS 2020–2024 total population.")
                put(g, "crime_violent_per_1k_est", round(1000 * v["crime_violent_est"] / pop[g], 1),
                    NOTE + " Residents: ACS 2020–2024 total population.")
        else:
            put(g, f"crime_total_est_{y}", round(v["crime_total_est"]), vintage=str(y))
    # Official citywide (City & County of Honolulu) Table 1, for reference and the trend line
    for y in years:
        k = "crime_total_est" if y == LATEST else f"crime_total_est_{y}"
        if (y, "index_total") in official:
            put("CNTY-15003", k, official[(y, "index_total")], f"HPD Table 1 official index total, {y} (UCR/SRS).",
                str(y), "direct")
    for off, k in (("violent_crime_total", "crime_violent_est"), ("property_crime_total", "crime_property_est")):
        if (LATEST, off) in official:
            put("CNTY-15003", k, official[(LATEST, off)], f"HPD Table 1 official total, {LATEST} (UCR/SRS).", method="direct")
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: HPD crime ESTIMATE, {n} observations, years {years[0]}–{years[-1]}")
    return n


if __name__ == "__main__":
    build()
