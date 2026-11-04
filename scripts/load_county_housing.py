"""
Load county-level housing and population context into the SQLite database.

Sources:
- UHERO Hawaiʻi Housing Factbook 2026 (median single-family home prices, 2025)
  https://uhero.hawaii.edu/the-hawaii-housing-factbook-2026/
- DBEDT 2025 State of Hawaii Data Book / Census Vintage 2025 population estimates
  (July 1, 2025 resident population)
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"

# County housing and population context
COUNTY_HOUSING = [
    # county, median_sf_price_2025, population_july2025
    ("Honolulu", 1110000, 988703),
    ("Maui", 1175000, 160674),
    ("Hawaii", 465000, 210043),
    ("Kauai", 1100000, 73400),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS county_housing (
            county TEXT PRIMARY KEY,
            median_sf_price_2025 INTEGER,
            population_july2025 INTEGER
        )
    """)
    cur.execute("DELETE FROM county_housing")
    cur.executemany(
        "INSERT INTO county_housing (county, median_sf_price_2025, population_july2025) VALUES (?, ?, ?)",
        COUNTY_HOUSING,
    )
    conn.commit()
    conn.close()
    print(f"Loaded {len(COUNTY_HOUSING)} county housing rows into {DB_PATH}")

if __name__ == "__main__":
    main()
