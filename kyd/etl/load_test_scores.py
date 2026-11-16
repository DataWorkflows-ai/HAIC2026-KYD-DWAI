"""HIDOE 2025 test results (Smarter Balanced ELA/Math, HSA Science) by district → kyd.sqlite.

  python kyd/etl/load_test_scores.py        (run after load_acs_profile.py; chained from it)

Inputs (data/raw/research/):
  doe_sba/SBA2024-25.xlsx, doe_sba/HSA-Science2024-25.xlsx  (HIDOE, SY2024-25, SHA256SUMS.txt alongside)
  team2a_school_meals_fr_by_school_SY2025-26_no_charter.csv  (HIDOE school code → 2022 House/Senate district,
                                                              by school location; the same map the meals data uses)
Method: for each non-charter school and grade, proficient = N tested × share met/exceeded. Grades are summed per
school (the "All Grades" rows are skipped so schools with one tested grade still count), then schools are summed
by district and the share recomputed. Cells suppressed under FERPA ("*") are left out, so district figures cover
the tested students HIDOE publishes. Rolled up by SCHOOL LOCATION, not where students live. Public charter schools
are excluded (they enroll statewide), per Mitchell's decision of 2026-11-16.
Licensing: HIDOE content is not for commercial use; figures are cited, not republished.
"""
from __future__ import annotations
import csv
import hashlib
import sqlite3
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "kyd" / "data" / "kyd.sqlite"
RAW = REPO / "data" / "raw" / "research"
SBA = RAW / "doe_sba" / "SBA2024-25.xlsx"
HSA = RAW / "doe_sba" / "HSA-Science2024-25.xlsx"
SCHOOL_MAP = RAW / "team2a_school_meals_fr_by_school_SY2025-26_no_charter.csv"
SRC = "hidoe_sba_2025"
URL = "https://hawaiipublicschools.org/academics/types-of-testing/"
# Niʻihau School (461) is not in the meals file; placed by its location (Puʻuwai) in the 2022 boundaries.
EXTRA = {461: (17, 8)}
NOTE = ("Share of tested students at public schools in the district who met or exceeded the standard. Rolled up by "
        "school location, not where students live. * Excludes public charter schools. Results suppressed by HIDOE "
        "for student privacy are left out.")
INDICATORS = {
    "pct_sba_ela_proficient": ("Students meeting the ELA standard (Smarter Balanced 2025)*", "pct", "ela"),
    "pct_sba_math_proficient": ("Students meeting the math standard (Smarter Balanced 2025)*", "pct", "math"),
    "pct_hsa_science_proficient": ("Students meeting the science standard (HSA 2025)*", "pct", "sci"),
    "sba_tested": ("Students tested, ELA (Smarter Balanced 2025)*", "count", "ela"),
}


def school_districts() -> dict[int, tuple[int, int]]:
    out = dict(EXTRA)
    for r in csv.DictReader(SCHOOL_MAP.open(encoding="utf-8")):
        if r["site_id"].isdigit() and r["house_2022"]:
            out[int(r["site_id"])] = (int(float(r["house_2022"])), int(float(r["senate_2022"])))
    return out


def _sheet(path: Path, cols: list[str]) -> pd.DataFrame:
    s = pd.read_excel(path, sheet_name="SCHOOLS", header=None, skiprows=7)
    s = s.iloc[:, :len(cols)]
    s.columns = cols
    s[["ca", "cx", "code", "name"]] = s[["ca", "cx", "code", "name"]].ffill()
    s["code"] = pd.to_numeric(s["code"], errors="coerce")
    s = s[s["code"].notna() & s["grade"].notna() & (s["grade"] != "All Grades") & (s["ca"] != "Charter")]
    s["code"] = s["code"].astype(int)
    return s


def school_rows() -> list[tuple[int, str, float, float]]:
    """(school code, subject, n tested, n proficient) per non-charter school, summed over grades."""
    acc: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    sba = _sheet(SBA, ["ca", "cx", "code", "name", "grade", "ela_n", "ela_p", "math_n", "math_p"])
    hsa = _sheet(HSA, ["ca", "cx", "code", "name", "grade", "sci_n", "sci_p"])
    for df, subjects in ((sba, ("ela", "math")), (hsa, ("sci",))):
        for r in df.itertuples():
            for sub in subjects:
                n, p = pd.to_numeric(getattr(r, f"{sub}_n"), errors="coerce"), pd.to_numeric(getattr(r, f"{sub}_p"), errors="coerce")
                if pd.isna(n) or pd.isna(p) or n <= 0:
                    continue  # suppressed ("*") or blank
                a = acc[(r.code, sub)]
                a[0] += float(n)
                a[1] += float(n) * float(p)
    return [(code, sub, n, prof) for (code, sub), (n, prof) in acc.items()]


def build() -> int:
    smap = school_districts()
    rows = school_rows()
    missing = sorted({code for code, *_ in rows} - set(smap))
    if missing:
        raise SystemExit(f"schools with no district: {missing}")
    tot: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for code, sub, n, prof in rows:
        hd, sd = smap[code]
        for geo in (f"HD-{hd:02d}", f"SD-{sd:02d}", "HI"):
            tot[(geo, sub)][0] += n
            tot[(geo, sub)][1] += prof
    c = sqlite3.connect(DB)
    keys = list(INDICATORS)
    c.execute(f"DELETE FROM observation WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute(f"DELETE FROM indicator WHERE indicator IN ({','.join('?' * len(keys))})", keys)
    c.execute("DELETE FROM source WHERE source_id = ?", (SRC,))
    sha = hashlib.sha256(SBA.read_bytes() + HSA.read_bytes() + SCHOOL_MAP.read_bytes()).hexdigest()[:16]
    c.execute("INSERT INTO source VALUES (?,?,?,?,?,?,?)",
              (SRC, "Hawaiʻi State Department of Education (HIDOE)", "2025 Smarter Balanced (ELA, math) and HSA "
               "Science results by school, rolled up to 2022 legislative districts by school location (charter "
               "schools excluded)", URL, "2025-09-01", "Cited figures; HIDOE content not for commercial use", sha))
    for k, (label, unit, _) in INDICATORS.items():
        c.execute("INSERT INTO indicator VALUES (?,?,?,?,?)", (k, label, unit, "education", "HIDOE SY2024-25"))
    n_obs = 0
    for (geo, sub), (n, prof) in sorted(tot.items()):
        for k, (_, unit, s) in INDICATORS.items():
            if s != sub:
                continue
            v = round(n) if unit == "count" else round(100 * prof / n, 1)
            note = NOTE if geo != "HI" else "Sum of all non-charter public schools. " + NOTE
            c.execute("INSERT INTO observation VALUES (?,?,?,?,?,?,?,?,?)",
                      (f"sba2025-{geo}-{k}", geo, k, v, None, "SY2024-25", "derived", note, SRC))
            n_obs += 1
    c.commit()
    c.close()
    state = {s: round(100 * tot[("HI", s)][1] / tot[("HI", s)][0], 1) for s in ("ela", "math", "sci")}
    print(f"{DB.relative_to(REPO)}: test scores, {n_obs} observations; non-charter state % {state}")
    return n_obs


if __name__ == "__main__":
    build()
