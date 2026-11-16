"""BESSD SFY 2026 monthly summary: data/raw/SFY-2026-SUMMARY.numbers → data/processed/bessd_sfy2026_caseload_by_island.csv.

The CSV is re-extracted from the Apple Numbers workbook and compared cell by cell. The extractor
finds blocks by their titles ("NUMBER OF PERSONS", "NUMBER OF HOUSEHOLDS") and the header row
(ISL/BR TANF TAONF GA SSI ABD NPA TOTAL), so a renamed block, a new column or a moved table is a
format failure instead of numbers silently landing in the wrong column.

Internal arithmetic is checked too: program columns add to TOTAL, Maui + Molokai + Lānaʻi = Maui
Branch, and the four branches add to STATE.
"""
from __future__ import annotations
import csv
from collections import defaultdict

from core import PROCESSED, RAW, Report

SRC = "dhs.bessd_sfy2026"
NUMBERS = RAW / "SFY-2026-SUMMARY.numbers"
CSV = PROCESSED / "bessd_sfy2026_caseload_by_island.csv"
COLS = ["TANF", "TAONF", "GA", "SSI", "ABD", "NPA", "TOTAL"]
BLOCKS = {"NUMBER OF PERSONS": "persons", "NUMBER OF HOUSEHOLDS": "households"}
CODES = ["OB", "HB", "KB", "Maui", "Molokai", "Lanai", "MB", "STATE"]
MONTHS = {"JUL": "2025-07", "AUG": "2025-08", "SEP": "2025-09", "OCT": "2025-10", "NOV": "2025-11", "DEC": "2025-12",
          "JAN": "2026-01", "FEB": "2026-02", "MAR": "2026-03", "APR": "2026-04", "MAY": "2026-05", "JUN": "2026-06"}


def extract(rep: Report) -> dict[tuple[str, str, str], list[float]] | None:
    try:
        from numbers_parser import Document
    except Exception as e:
        rep.add(f"{SRC}.parser", SRC, "provenance", "warn",
                f"numbers-parser not installed ({type(e).__name__}); workbook not re-read, CSV checked on its own")
        return None
    doc = Document(str(NUMBERS))
    out: dict[tuple[str, str, str], list[float]] = {}
    for sheet in doc.sheets:
        month = MONTHS.get(sheet.name)
        if not month:
            continue
        rows = [[c.value for c in r] for r in sheet.tables[0].rows()]
        found = set()
        for i, r in enumerate(rows):
            title = str(r[0] or "").strip().upper()
            if title not in BLOCKS:
                continue
            header = [str(x or "").strip().upper() for x in rows[i + 1][:8]]
            if not rep.expect(header == ["ISL/BR"] + COLS, f"{SRC}.{sheet.name}.{BLOCKS[title]}.header", SRC, "format",
                              f"{sheet.name} “{title}” header is ISL/BR + {' '.join(COLS)}",
                              expected=["ISL/BR"] + COLS, actual=header, location=sheet.name):
                continue
            found.add(BLOCKS[title])
            for r2 in rows[i + 2: i + 2 + len(CODES)]:
                code = str(r2[0] or "").strip()
                vals = r2[1:8]
                if code in CODES and all(isinstance(v, (int, float)) for v in vals):
                    out[(month, BLOCKS[title], code)] = [float(v) for v in vals]
        # months not yet reported are template rows of zeros: drop them
        if all(not any(v) for k, v in out.items() if k[0] == month):
            for k in [k for k in out if k[0] == month]:
                del out[k]
        has_data = any(k[0] == month for k in out)
        if has_data or month <= "2026-02":
            rep.expect(found == set(BLOCKS.values()), f"{SRC}.{sheet.name}.blocks", SRC, "format",
                       f"{sheet.name}: persons and households blocks found", actual=sorted(found), location=sheet.name,
                       fail_status="fail" if has_data else "warn")
    return out


def run(rep: Report) -> None:
    if not rep.expect(NUMBERS.exists(), f"{SRC}.present", SRC, "provenance", "BESSD workbook archived in data/raw"):
        return
    rows = list(csv.DictReader(CSV.open()))
    csv_vals = {(r["month"], r["metric"], r["code"]): [float(r[c.lower()]) for c in COLS] for r in rows}

    wb = extract(rep)
    if wb is not None:
        diff = [f"{k}: csv {csv_vals.get(k)} vs workbook {v}" for k, v in sorted(wb.items()) if csv_vals.get(k) != v]
        extra = sorted(set(csv_vals) - set(wb))
        rep.expect(not diff, f"{SRC}.csv_matches_workbook", SRC, "transcription",
                   "every CSV row equals the workbook cell values", actual=diff[:8] or None,
                   location=f"{len(diff)} of {len(wb)} rows differ" if diff else f"{len(wb)} rows")
        rep.expect(not extra, f"{SRC}.csv_no_orphans", SRC, "transcription", "no CSV rows missing from the workbook",
                   actual=[str(x) for x in extra[:8]] or None)

    bad_tot = [k for k, v in csv_vals.items() if abs(sum(v[:-1]) - v[-1]) > 0.5]
    rep.expect(not bad_tot, f"{SRC}.row_totals", SRC, "consistency", "TANF+TAONF+GA+SSI+ABD+NPA = TOTAL on every row",
               actual=[str(k) for k in bad_tot[:8]] or None)
    by = defaultdict(dict)
    for (m, met, code), v in csv_vals.items():
        by[(m, met)][code] = v
    bad_mb, bad_state = [], []
    for k, d in by.items():
        if all(c in d for c in ("Maui", "Molokai", "Lanai", "MB")):
            if any(abs(d["Maui"][i] + d["Molokai"][i] + d["Lanai"][i] - d["MB"][i]) > 0.5 for i in range(7)):
                bad_mb.append(k)
        if all(c in d for c in ("OB", "HB", "KB", "MB", "STATE")):
            if any(abs(d["OB"][i] + d["HB"][i] + d["KB"][i] + d["MB"][i] - d["STATE"][i]) > 0.5 for i in range(7)):
                bad_state.append(k)
    rep.expect(not bad_mb, f"{SRC}.maui_branch_sum", SRC, "consistency", "Maui + Molokaʻi + Lānaʻi = Maui Branch",
               actual=[str(k) for k in bad_mb] or None)
    rep.expect(not bad_state, f"{SRC}.state_sum", SRC, "consistency", "OB + HB + KB + MB = STATE",
               actual=[str(k) for k in bad_state] or None)
