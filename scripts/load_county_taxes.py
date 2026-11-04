"""
Load county-level General Excise Tax and Transient Accommodation Tax
liabilities into the SQLite database.

Source: Hawaii DOTAX monthly reports, May 2026 filing period
- GET Liability by District: https://files.hawaii.gov/tax/stats/monthly/202605liab-by-d_ge.pdf
- TAT Liability by District: https://files.hawaii.gov/tax/stats/monthly/202605liab-by-d_tat.pdf
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"

# May 2026 tax liabilities (dollars) by county / tax district
# Grand totals from the liability-by-district reports
COUNTY_TAXES = [
    # county, get_liability_may2026, tat_liability_may2026
    ("Honolulu", 241472839, 28856798),
    ("Maui", 56831260, 19231754),
    ("Hawaii", 51485113, 9563242),
    ("Kauai", 25749225, 9290632),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS county_taxes (
            county TEXT PRIMARY KEY,
            get_liability_may2026 INTEGER,
            tat_liability_may2026 INTEGER
        )
    """)
    cur.execute("DELETE FROM county_taxes")
    cur.executemany(
        "INSERT INTO county_taxes (county, get_liability_may2026, tat_liability_may2026) VALUES (?, ?, ?)",
        COUNTY_TAXES,
    )
    conn.commit()
    conn.close()
    print(f"Loaded {len(COUNTY_TAXES)} county tax rows into {DB_PATH}")

if __name__ == "__main__":
    main()
