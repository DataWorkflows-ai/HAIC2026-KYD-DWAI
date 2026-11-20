"""USDA Reaching Those in Need FY 2022 technical report (data/raw/research/usda/) vs the Hawaiʻi figures typed
into kyd/etl/load_programs.py, which set the benchmark end of the SNAP gap range.

Each figure is re-read from the Hawaiʻi row of the table the ETL cites. A missing table or row is a format change;
a different number is a transcription error.
"""
from __future__ import annotations
import re
import sys

from core import RAW, REPO, Report

PDF = RAW / "research" / "usda" / "ear-SNAP-Participation-Rates-2022.pdf"
SRC = "usda.snap_rates_fy2022"

# table heading → the Hawaiʻi row's numbers in column order
TABLES = {
    "Table III.1.": "rate FY2020, rate FY2022, eligible (thousands) FY2020, FY2022",
    "Table III.3.": "rate lower, rate upper, eligible lower, eligible upper (FY 2022)",
    "Table A.3.": "eligible participants FY2020, FY2022",
    "Table A.18.": "eligible FY2020, FY2022, SE FY2020, SE FY2022",
}


def hawaii_row(text: str) -> list[float] | None:
    m = re.search(r"^Hawaii\*?((?:\s+[\d,]+(?:\.\d+)?)+)\s*$", text, re.M)
    return [float(x.replace(",", "")) for x in m.group(1).split()] if m else None


def run(rep: Report) -> None:
    if not rep.expect(PDF.exists(), f"{SRC}.present", SRC, "provenance", "USDA FY 2022 technical report archived"):
        return
    import pypdf
    pages = [p.extract_text() or "" for p in pypdf.PdfReader(str(PDF)).pages]
    rows = {}
    for table, cols in TABLES.items():
        row = next((r for t in pages if table in t and (r := hawaii_row(t))), None)   # skip pages that only cite it
        if rep.expect(row is not None, f"{SRC}.format.{table.strip('.').lower().replace(' ', '_')}", SRC, "format",
                      f"{table} has a Hawaiʻi row ({cols})", actual=row):
            rows[table] = row

    sys.path.insert(0, str(REPO / "kyd" / "etl"))
    import load_programs as lp
    want = {  # check id → (value in the ETL, table, column index)
        "rate": (lp.SNAP_RATE_HI, "Table III.1.", 1),
        "rate_ci_low": (lp.SNAP_RATE_CI_HI[0], "Table III.3.", 0),
        "rate_ci_high": (lp.SNAP_RATE_CI_HI[1], "Table III.3.", 1),
        "participants": (lp.SNAP_PARTICIPANTS_HI, "Table A.3.", 1),
        "eligible": (lp.SNAP_ELIGIBLE_HI[0], "Table A.18.", 1),
        "eligible_moe": (lp.SNAP_ELIGIBLE_HI[1], "Table A.18.", 3),
    }
    for key, (code, table, i) in want.items():
        if table not in rows:
            continue
        pdf = rows[table][i] * (1.645 if key == "eligible_moe" else 1)
        rep.expect(round(pdf) == code, f"{SRC}.transcription.{key}", SRC, "transcription",
                   f"load_programs.py Hawaiʻi {key} matches {table}", expected=round(pdf), actual=code)
