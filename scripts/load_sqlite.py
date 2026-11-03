"""
Load the processed ACS CSVs into a local SQLite database.
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "districts.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    
    house = pd.read_csv(PROCESSED_DIR / "house_districts.csv")
    senate = pd.read_csv(PROCESSED_DIR / "senate_districts.csv")
    
    house.to_sql("house_districts", conn, if_exists="replace", index=False)
    senate.to_sql("senate_districts", conn, if_exists="replace", index=False)
    
    conn.close()
    print(f"Created {DB_PATH}")
    print(f"House rows: {len(house)}, Senate rows: {len(senate)}")

if __name__ == "__main__":
    main()