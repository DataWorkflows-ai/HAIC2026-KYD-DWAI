"""
Load county/island SNAP participation into the SQLite database.

Source: Hawaiʻi DHS BESSD SFY 2026 monthly summary workbook (data/raw/SFY-2026-SUMMARY.numbers),
read through data/processed/bessd_sfy2026_caseload_by_island.csv. kyd/verify/bessd.py re-extracts
that CSV from the workbook and compares it cell by cell, so these figures are traceable to an
archived source file.

Usage: python scripts/load_county_snap.py [--month YYYY-MM]   (default: latest month in the CSV)
"""

import argparse
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"
BESSD_CSV = ROOT / "data" / "processed" / "bessd_sfy2026_caseload_by_island.csv"
SOURCE = "dhs.bessd_sfy2026"

# county key used by the app → (BESSD island/branch code, display label)
COUNTIES = [
    ("Honolulu", "OB", "Oʻahu"),
    ("Hawaii", "HB", "Hawaiʻi County"),
    ("Maui", "Maui", "Maui Island"),
    ("Kauai", "KB", "Kauaʻi"),
    ("Molokai", "Molokai", "Molokaʻi"),
    ("Lanai", "Lanai", "Lānaʻi"),
]


def county_snap(month: str | None = None) -> tuple[str, list[tuple]]:
    """Return (month, rows) where rows are (county, households, individuals, notes)."""
    rows = list(csv.DictReader(BESSD_CSV.open(encoding="utf-8")))
    month = month or max(r["month"] for r in rows)
    idx = {(r["metric"], r["code"]): r for r in rows if r["month"] == month}
    if not idx:
        raise SystemExit(f"No BESSD rows for month {month}")
    out = []
    for county, code, label in COUNTIES:
        try:
            hh = int(float(idx[("households", code)]["total"]))
            persons = int(float(idx[("persons", code)]["total"]))
        except KeyError:
            raise SystemExit(f"BESSD {month} is missing {code} households/persons")
        out.append((county, hh, persons, label))
    return month, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="YYYY-MM (default: latest in BESSD CSV)")
    month, rows = county_snap(ap.parse_args().month)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS county_snap")
    cur.execute("""
        CREATE TABLE county_snap (
            county TEXT PRIMARY KEY,
            households INTEGER,
            individuals INTEGER,
            notes TEXT,
            month TEXT,
            source TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO county_snap (county, households, individuals, notes, month, source) VALUES (?, ?, ?, ?, ?, ?)",
        [r + (month, SOURCE) for r in rows],
    )
    conn.commit()
    conn.close()
    print(f"Loaded {len(rows)} county SNAP rows ({month}, {SOURCE}) into {DB_PATH}")


if __name__ == "__main__":
    main()
