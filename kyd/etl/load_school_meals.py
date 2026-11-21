"""Free and reduced-price school meals by district (SY2025-26) → kyd.sqlite.

  python kyd/etl/load_school_meals.py        (run after load_acs_profile.py)

Input: data/raw/research/team2a_school_meals_fr_by_{house,senate}_district_SY2025-26_no_charter.csv, the
research team's rollup of Hawaiʻi Child Nutrition Programs "October Data" SY2025-26 (per-school enrollment and
free/reduced-eligible counts) to 2022 districts by SCHOOL LOCATION, not student residence. Public charter
schools are excluded (they enroll statewide), per Mitchell's decision of 2026-11-15.
Licensing: HIDOE/HCNP content is not for commercial use; figures are cited, not republished (data/raw/research/LICENSING.md).
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
RAW = REPO / "data" / "raw" / "research"
SRC = "hcnp_october_sy2025_26"
URL = "https://hcnp.hawaii.gov/wp-content/uploads/2026/01/October-Data-2026-SY25-26.pdf"
NOTE = ("Rolled up by school location, not where students live. * Excludes public charter schools, which enroll "
        "students statewide regardless of district. Counts eligibility in the October report, not meals served.")
INDICATORS = {
    "pct_free_reduced_meals": ("Public-school students eligible for free/reduced-price meals*", "pct"),
    "free_reduced_students": ("Students eligible for free/reduced-price meals (not meals served)*", "count"),
    "public_school_enrolled": ("Public-school enrollment (schools in district)*", "count"),
    "cep_participating_schools": ("CEP participating schools (HCNP workbook)", "count"),
    "cep_eligible_not_participating_schools": ("CEP-eligible schools not participating", "count"),
    "cep_not_participating_enrolled": ("Enrollment at CEP-eligible non-participating schools", "count"),
    "cep_not_participating_uncertified": ("Students not certified at CEP-eligible non-participating schools", "count"),
}


def build() -> int:
    files = {"HD": RAW / "team2a_school_meals_fr_by_house_district_SY2025-26_no_charter.csv",
             "SD": RAW / "team2a_school_meals_fr_by_senate_district_SY2025-26_no_charter.csv"}
    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    c.execute(f"DELETE FROM observation WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    sha = hashlib.sha256(b"".join(f.read_bytes() for f in files.values())).hexdigest()[:16]
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Hawaiʻi Child Nutrition Programs (HIDOE)", "October Data SY2025-26: free and reduced-price "
               "eligibility by school, rolled up to 2022 legislative districts (charter schools excluded)", URL,
               "2026-01-01", "Cited figures; HIDOE content not for commercial use", sha))
    for k, (label, unit) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, "education", "HCNP Oct SY2025-26"))
    n, tot = 0, {"enrolled": 0, "fr": 0}
    for prefix, path in files.items():
        for r in csv.DictReader(path.open(encoding="utf-8")):
            col = "house_2022" if prefix == "HD" else "senate_2022"
            geo = f"{prefix}-{int(float(r[col])):02d}"
            enr, fr = float(r["enrolled"]), float(r["free_reduced"])
            vals = {"pct_free_reduced_meals": round(100 * fr / enr, 2) if enr else None,
                    "free_reduced_students": fr, "public_school_enrolled": enr}
            if prefix == "HD":
                tot["enrolled"] += enr
                tot["fr"] += fr
            for k, v in vals.items():
                c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                          (f"meals2526-{geo}-{k}", geo, k, v, None, "SY2025-26", "derived", NOTE, SRC))
                n += 1
    state = {"pct_free_reduced_meals": round(100 * tot["fr"] / tot["enrolled"], 2),
             "free_reduced_students": tot["fr"], "public_school_enrolled": tot["enrolled"],
             "cep_participating_schools": 118, "cep_eligible_not_participating_schools": 74,
             "cep_not_participating_enrolled": 45_902, "cep_not_participating_uncertified": 22_270}
    for k, v in state.items():
        c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                  (f"meals2526-HI-{k}", "HI", k, v, None, "SY2025-26", "derived",
                   ("HCNP CEP SY2026-27 workbook joined to October SY2025-26 school rows. "
                    if k.startswith("cep_") else "Sum of the 51 House districts (non-charter public schools). ") + NOTE, SRC))
        n += 1
    c.commit()
    c.close()
    print(f"{DB.relative_to(REPO)}: school meals, {n} observations; state {state}")
    return n


if __name__ == "__main__":
    build()
