"""
Load county-level SNAP participation numbers into the SQLite database.

Source: Hawaii DHS BESSD testimony, September 2025
https://www.capitol.hawaii.gov/sessions/session2025/testimony/INFO_TESTIMONY_HHS_10-28-25_DHS.pdf
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"

# September 2025 SNAP participation (households)
COUNTY_SNAP = [
    ("Honolulu", 50729, 100064, "Oʻahu"),
    ("Hawaii", 21654, 41673, "Hawaiʻi County"),
    ("Maui", 8112, 15845, "Maui Island"),
    ("Kauai", 4438, 8599, "Kauaʻi"),
    ("Molokai", 1136, 2380, "Molokaʻi"),
    ("Lanai", 160, 386, "Lānaʻi"),
]

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS county_snap (
            county TEXT PRIMARY KEY,
            households INTEGER,
            individuals INTEGER,
            notes TEXT
        )
    """)
    cur.execute("DELETE FROM county_snap")
    cur.executemany(
        "INSERT INTO county_snap (county, households, individuals, notes) VALUES (?, ?, ?, ?)",
        COUNTY_SNAP,
    )
    conn.commit()
    conn.close()
    print(f"Loaded {len(COUNTY_SNAP)} county SNAP rows into {DB_PATH}")

if __name__ == "__main__":
    main()
