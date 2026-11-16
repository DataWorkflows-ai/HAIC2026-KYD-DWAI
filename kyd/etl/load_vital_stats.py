"""Births and deaths by 2022 House/Senate district, 2000–2024 (ESTIMATE) → kyd.sqlite.

  python kyd/etl/load_vital_stats.py     (chained from load_acs_profile.py)

Input: data/raw/research/vital_stats/vital_stats_births_deaths_by_{house,senate}_district_ESTIMATE.csv, built by the
research team from Hawaiʻi-IBIS resident birth and death counts by community (Hawaiʻi DOH, Hawaii Health Data
Warehouse) allocated to districts with 2020 Census block population (see METHOD.md and RECONCILIATION.csv beside it).
No agency publishes these by district, so every value is labelled ESTIMATE. District sums equal the IBIS community
totals and land within about 1% of the DBEDT/DOH state totals for 2024.
Shown here: the 2020–2024 average per year (pooled, as METHOD.md advises for small areas), a crude rate per 1,000
residents (ACS 2020–2024 population), and the yearly series 2000–2024 for the trend chart.
IBIS terms: statistical reporting and analysis only.
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
RAW = REPO / "data" / "raw" / "research" / "vital_stats"
FILES = {"HD": RAW / "vital_stats_births_deaths_by_house_district_ESTIMATE.csv",
         "SD": RAW / "vital_stats_births_deaths_by_senate_district_ESTIMATE.csv"}
SRC = "hi_ibis_vital_est"
URL = "https://hhdw.org/report/"
YEARS = range(2000, 2025)
NOTE = ("ESTIMATE: Hawaiʻi-IBIS resident counts by community (DOH) allocated to 2022 districts by 2020 Census block "
        "population; not published by any agency. Assumes events spread with total population (no age adjustment).")
IND = {
    "births_avg_est": ("Births per year, 2020–2024 average (ESTIMATE)", "count", "health"),
    "deaths_avg_est": ("Deaths per year, 2020–2024 average (ESTIMATE)", "count", "health"),
    "birth_rate_per_1k_est": ("Births per 1,000 residents, 2020–2024 (ESTIMATE)", "per_1000", "health"),
    "death_rate_per_1k_est": ("Deaths per 1,000 residents, 2020–2024 (ESTIMATE, not age-adjusted)", "per_1000", "health"),
}


def build() -> int:
    c = sqlite3.connect(DB)
    pop = dict(c.execute("SELECT geo_id, value FROM observation WHERE indicator='total_pop'").fetchall())
    trend_keys = [f"{k}_est_{y}" for k in ("births", "deaths") for y in YEARS]
    keys = list(IND) + trend_keys
    c.execute(f"DELETE FROM observation WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    sha = hashlib.sha256(b"".join(f.read_bytes() for f in FILES.values())).hexdigest()[:16]
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Hawaiʻi State Department of Health, Hawaii Health Data Warehouse (Hawaiʻi-IBIS); district allocation by research agent (ESTIMATE)",
               "Live births and all-cause deaths by community of residence, 2000–2024, allocated to 2022 legislative districts by 2020 block population",
               URL, "2026-01-05", "IBIS terms: statistical reporting and analysis only", sha))
    for k, (label, unit, topic) in IND.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, topic, "IBIS"))
    for k in ("births", "deaths"):
        for y in YEARS:
            c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)",
                      (f"{k}_est_{y}", f"{k.title()}, {y} (ESTIMATE)", "count", "vital_trend", "IBIS"))
    n = 0
    state = defaultdict(float)
    for prefix, path in FILES.items():
        series: dict[str, dict[int, tuple[float, float]]] = defaultdict(dict)
        flags: dict[str, float] = defaultdict(float)
        for r in csv.DictReader(path.open(encoding="utf-8")):
            g = f"{prefix}-{int(r['district']):02d}"
            series[g][int(r["year"])] = (float(r["births_est"]), float(r["deaths_est"]))
            flags[g] = max(flags[g], float(r["share_suppressed_deaths"] or 0), float(r["share_suppressed_births"] or 0))
        for g, ys in series.items():
            b5 = sum(ys[y][0] for y in range(2020, 2025)) / 5
            d5 = sum(ys[y][1] for y in range(2020, 2025)) / 5
            note = NOTE + (" Some suppressed IBIS cells (counts under 9) touch this district and were not allocated."
                           if flags[g] > 0 else "")
            vals = {"births_avg_est": round(b5), "deaths_avg_est": round(d5)}
            if pop.get(g):
                vals["birth_rate_per_1k_est"] = round(1000 * b5 / pop[g], 1)
                vals["death_rate_per_1k_est"] = round(1000 * d5 / pop[g], 1)
            for k, v in vals.items():
                c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                          (f"vital-{g}-{k}", g, k, v, None, "2020-2024", "derived", note, SRC)); n += 1
            for y, (b, d) in ys.items():
                for k, v in (("births", b), ("deaths", d)):
                    c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                              (f"vital-{g}-{k}-{y}", g, f"{k}_est_{y}", round(v, 1), None, str(y), "derived", note, SRC)); n += 1
            if prefix == "HD":
                state["b5"] += b5; state["d5"] += d5
                for y, (b, d) in ys.items():
                    state[f"births_{y}"] += b; state[f"deaths_{y}"] += d
    hi = {"births_avg_est": round(state["b5"]), "deaths_avg_est": round(state["d5"])}
    if pop.get("HI"):
        hi["birth_rate_per_1k_est"] = round(1000 * state["b5"] / pop["HI"], 1)
        hi["death_rate_per_1k_est"] = round(1000 * state["d5"] / pop["HI"], 1)
    for k, v in hi.items():
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"vital-HI-{k}", "HI", k, v, None, "2020-2024", "derived", "Sum of the 51 House district estimates. " + NOTE, SRC)); n += 1
    for y in YEARS:
        for k in ("births", "deaths"):
            c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                      (f"vital-HI-{k}-{y}", "HI", f"{k}_est_{y}", round(state[f"{k}_{y}"], 1), None, str(y), "derived",
                       "Sum of the 51 House district estimates. " + NOTE, SRC)); n += 1
    c.commit(); c.close()
    print(f"{DB.relative_to(REPO)}: births/deaths ESTIMATE, {n} observations; state 2024 births {state['births_2024']:.0f}, deaths {state['deaths_2024']:.0f}")
    return n


if __name__ == "__main__":
    build()
