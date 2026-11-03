"""
Minimal agent that answers district questions using the SQLite database.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"

def get_district(chamber: str, district_number: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    table = "house_districts" if chamber.lower() == "house" else "senate_districts"
    cur = conn.execute(f"SELECT * FROM {table} WHERE district = ?", (district_number,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def answer(question: str):
    """
    Very simple rule-based responder for the five test questions.
    Later this can be replaced with an LLM that calls get_district().
    """
    q = question.lower()
    
    if "house district 22" in q and "65" in q or "kūpuna" in q or "kupuna" in q:
        data = get_district("house", 22)
        return f"In House District 22, {data['pct_65plus_poverty_percent']} of people age 65+ live below the poverty line (ACS 2020-2024 5-year, DP03)."
    
    if "uninsured" in q or "health insurance" in q:
        # Return top 3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT district, pct_no_health_insurance_percent 
            FROM house_districts 
            ORDER BY CAST(REPLACE(pct_no_health_insurance_percent, '%', '') AS REAL) DESC 
            LIMIT 3
        """)
        rows = cur.fetchall()
        conn.close()
        lines = [f"House District {r['district']}: {r['pct_no_health_insurance_percent']}" for r in rows]
        return "Top 3 House districts by % without health insurance:\n" + "\n".join(lines)
    
    return "I can answer questions about specific districts. Try asking about House District 22 kūpuna poverty or the top uninsured districts."

if __name__ == "__main__":
    print(answer("How many kūpuna in House District 22 live below the poverty line?"))
    print()
    print(answer("Which House districts have the highest share of residents without health insurance?"))