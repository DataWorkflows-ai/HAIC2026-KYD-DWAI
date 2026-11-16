"""DHS Databook 2025 (data/raw/DHS-Databook-2025.pdf) vs the figures typed into Crystal's scripts.

Every hand-entered Databook number in scripts/*.py and data/processed/*databook*.json is re-read
from the PDF on the page the code cites. Two things are caught:

  transcription  the number in code differs from the number in the PDF
  format         the table is no longer where the code says (page moved, heading renamed,
                 columns reordered) — reported with where the heading now is, if anywhere

Page numbers are PDF page indexes (1-based), as the scripts cite them; the printed folio is
different (PDF page 27 is printed page 24).
"""
from __future__ import annotations
import json
import re
import sys

from core import PROCESSED, RAW, REPO, Report

PDF = RAW / "DHS-Databook-2025.pdf"
SRC = "dhs.databook2025"

# heading → page the scripts rely on. A missing heading is a format change.
ANCHORS = [
    (4, "Aid to Aged, Blind & Disabled (AABD)"),
    (5, "General Assistance (GA)"),
    (6, "Supplemental Nutrition Assistance Program (SNAP)"),
    (8, "Temporary Assistance for Needy Families (TANF)"),
    (12, "Federal Poverty Guidelines"),
    (12, "Population in Poverty (Percent)"),
    (12, "Individuals Below Percentages of Poverty Level"),
    (12, "50% 125% 150% 185% 200%"),
    (13, "Children and Youth in Poverty"),
    (27, "NUMBER OF RECIPIENTS"),
    (27, "SFY Statewide Oahu Hawaii Maui Kauai Molokai Lanai"),
]


def norm(t: str) -> str:
    t = t.replace("–", "-").replace("—", "-").replace(" ", " ")
    t = re.sub(r"\s*/\s*", "/", t)
    t = re.sub(r"(\d)\s*-\s*(\d)", r"\1-\2", t)
    t = re.sub(r"(\d)\s+\+", r"\1+", t)                     # "80 + 20%" → "80+ 20%"
    return re.sub(r"\s+", " ", t).strip()


def pages() -> list[str]:
    import pypdf
    return [p.extract_text() or "" for p in pypdf.PdfReader(str(PDF)).pages]


def section(text: str, start: str, end: str | None = None) -> str:
    t = norm(text)
    i = t.find(norm(start))
    if i < 0:
        return ""
    j = t.find(norm(end), i + 1) if end else -1
    return t[i: j if j > 0 else None]


def year_rows(text: str, n: int) -> dict[int, list[float]]:
    """Rows that start with a year followed by n numbers ($, %, commas stripped)."""
    out = {}
    tok = r"\$?[\d,]+(?:\.\d+)?%?"
    for m in re.finditer(rf"(?<!\d)((?:19|20)\d{{2}})((?:\s+{tok}){{{n}}})(?!\d)", text):
        y = int(m.group(1))
        if y not in out:
            out[y] = [float(x.strip("$%").replace(",", "")) for x in m.group(2).split()]
    return out


def pct_after(text: str, label: str) -> str | None:
    """'Female 65%' → '65'; '65-79+ <1%' → '<1'."""
    m = re.search(rf"(?<![A-Za-z]){re.escape(norm(label))}\s*([<>]?\s*\.?\d+(?:\.\d+)?)\s*%", text)
    return m.group(1).replace(" ", "") if m else None


def _scripts():
    sys.path.insert(0, str(REPO / "scripts"))
    import aabd, ga_proxy, medquest, tanf_by_island, tanf_underenrollment  # noqa: E401
    return aabd, ga_proxy, medquest, tanf_by_island, tanf_underenrollment


def run(rep: Report) -> None:
    if not rep.expect(PDF.exists(), f"{SRC}.present", SRC, "provenance", "Databook PDF archived in data/raw"):
        return
    P = pages()
    rep.expect(len(P) == 31, f"{SRC}.page_count", SRC, "format", "31 pages (2025 edition)", expected=31, actual=len(P))

    # 1. headings where the code expects them
    for pg, a in ANCHORS:
        here = norm(a) in norm(P[pg - 1]) if pg <= len(P) else False
        where = [i + 1 for i, t in enumerate(P) if norm(a) in norm(t)]
        rep.expect(here, f"{SRC}.anchor.p{pg}.{re.sub(r'[^a-z0-9]+', '_', a.lower())[:40]}", SRC, "format",
                   f"“{a}” is on page {pg}", expected=pg, actual=where or "not found", location=f"p{pg}")

    aabd, ga, mq, tbi, tue = _scripts()

    def caseload(pg, label, name, clients, cases, benefits):
        rows = year_rows(norm(P[pg - 1]), 3)
        got = rows.get(2025)
        rep.expect(got == [clients, cases, benefits], f"{SRC}.{name}.caseload_2025", SRC, "transcription",
                   f"{label} SFY 2025 clients, cases, benefits match page {pg}",
                   expected=got, actual=[clients, cases, benefits], location=f"p{pg}")

    def profile(pg, name, label_map: dict, values: dict, block: str):
        text = norm(P[pg - 1])
        for key, val in values.items():
            label = label_map.get(key, key)
            got = pct_after(text, label)
            cid = f"{SRC}.{name}.{block}.{re.sub(r'[^a-z0-9]+', '_', str(key).lower())}"
            if got is None:
                rep.add(cid, SRC, "format", "fail", f"{name} {block} “{label}” not found on page {pg}",
                        expected=val, location=f"p{pg}")
            elif isinstance(val, str):                         # code kept the PDF's "< 1" text
                same = got.replace(" ", "") == val.replace(" ", "").rstrip("%")
                rep.expect(same, cid, SRC, "transcription", f"{name} {block} “{label}” = {val} (page {pg})",
                           expected=f"{got}%", actual=val, location=f"p{pg}")
            elif got.startswith(("<", ">")):
                ok = float(val) <= 1
                rep.add(cid, SRC, "transcription", "warn" if ok else "fail",
                        f"{name} {block} “{label}”: PDF says {got}%, code uses {val}",
                        expected=f"{got}%", actual=val, location=f"p{pg}")
            else:
                rep.expect(float(got) == float(val), cid, SRC, "transcription",
                           f"{name} {block} “{label}” = {val}% (page {pg})", expected=float(got), actual=val,
                           location=f"p{pg}")
        total = sum(float(v) if not isinstance(v, str) else 0.0 for v in values.values())
        rep.expect(abs(total - 100) <= 2, f"{SRC}.{name}.{block}.sums_to_100", SRC, "consistency",
                   f"{name} {block} percentages add to 100 ± 2 (rounding)", actual=total, fail_status="warn")

    # 2. AABD (page 4), GA (page 5), TANF race (page 8)
    A = aabd.AABD_STATEWIDE
    caseload(4, "AABD", "aabd", A["sfy_2025_avg_monthly_clients"], A["sfy_2025_avg_monthly_cases"], A["sfy_2025_total_benefits"])
    for block in ("sex", "age", "race_ethnicity", "citizenship"):
        profile(4, "aabd", {"COFA": "(COFA)"}, A[block], block)
    G = ga.GA_STATEWIDE
    caseload(5, "GA", "ga", G["sfy_2025_avg_monthly_clients"], G["sfy_2025_avg_monthly_cases"], G["sfy_2025_total_benefits"])
    for block in ("sex", "age", "race_ethnicity", "citizenship"):
        profile(5, "ga", {"COFA": "(COFA)"}, G[block], block)
    profile(8, "tanf", {"hawaiian": "Hawaiian/part-Hawaiian", "caucasian": "Caucasian",
                        "other_pacific_islander": "Other Pacific Islander", "filipino": "Filipino",
                        "other_asian": "Other Asian", "black": "Black", "aian": "American Indian/Alaskan"},
            tue.TANF_STATEWIDE, "race_ethnicity")

    # 3. SNAP (page 6), from the processed JSON
    sj = json.loads((PROCESSED / "dhs_snap_demographics_june2025.json").read_text())
    c = sj["sfy_2025_caseload"]
    caseload(6, "SNAP", "snap", c["avg_monthly_clients"], c["avg_monthly_cases"], c["total_benefits"])
    for block, items in sj["demographics_june_2025"].items():
        vals = {i["category"]: i["percent"] for i in items}
        profile(6, "snap", {}, vals, block)

    # 4. Med-QUEST recipients by island (page 27)
    rows = year_rows(section(P[26], "NUMBER OF RECIPIENTS"), 7)
    for r in mq.ENROLLMENT:
        want = [r["statewide"], r["oahu"], r["hawaii"], r["maui"], r["kauai"], r["molokai"], r["lanai"]]
        rep.expect(rows.get(r["sfy"]) == want, f"{SRC}.medquest.sfy{r['sfy']}", SRC, "transcription",
                   f"Med-QUEST SFY {r['sfy']} recipients by island match page 27", expected=rows.get(r["sfy"]),
                   actual=want, location="p27")
        diff = sum(want[1:]) - want[0]
        rep.add(f"{SRC}.medquest.sfy{r['sfy']}.islands_sum", SRC, "consistency",
                "pass" if diff == 0 else "warn" if abs(diff) <= 5 else "fail",
                f"SFY {r['sfy']}: islands add up to statewide" + ("" if diff == 0 else
                f" (off by {diff:+d} in the Databook itself; the code matches the PDF)"),
                expected=want[0], actual=sum(want[1:]), location="p27")
    missing = sorted(set(rows) - {r["sfy"] for r in mq.ENROLLMENT})
    rep.expect(not missing, f"{SRC}.medquest.years_complete", SRC, "transcription",
               "every SFY on page 27 is in medquest.ENROLLMENT", actual=missing or None, fail_status="warn")

    # 5. Poverty tables (pages 12–13), from the processed JSON and tanf_by_island
    pj = json.loads((PROCESSED / "dhs_databook_census_poverty_estimates.json").read_text())
    p12 = P[11]
    county = year_rows(section(p12, "Population in Poverty (Percent)", "Individuals Below"), 4)
    for r in pj["population_in_poverty_percent_by_county"]:
        want = [r["honolulu"], r["hawaii"], r["kauai"], r["maui"]]
        rep.expect(county.get(r["year"]) == want, f"{SRC}.poverty_pct_county.{r['year']}", SRC, "transcription",
                   f"county poverty % {r['year']} match page 12", expected=county.get(r["year"]), actual=want, location="p12")
    t24 = [tbi.POVERTY_RATE_2024[k] for k in ("OAHU", "HAWAII", "KAUAI", "MAUI")]
    rep.expect(county.get(2024) == t24, f"{SRC}.tanf_by_island.poverty_2024", SRC, "transcription",
               "tanf_by_island.POVERTY_RATE_2024 matches page 12", expected=county.get(2024), actual=t24, location="p12")
    ladder = year_rows(section(p12, "Individuals Below Percentages of Poverty Level"), 5)
    for r in pj["individuals_below_percent_of_poverty_hawaii"]:
        want = [r["pct_50"], r["pct_125"], r["pct_150"], r["pct_185"], r["pct_200"]]
        rep.expect(ladder.get(r["year"]) == want, f"{SRC}.poverty_ladder.{r['year']}", SRC, "transcription",
                   f"people below 50–200% of poverty {r['year']} match page 12", expected=ladder.get(r["year"]),
                   actual=want, location="p12")
    kids = year_rows(section(P[12], "Children and Youth in Poverty", "DEFINITION"), 4)
    for r in pj.get("children_under_18_in_poverty_percent_by_county", []):
        want = [r["honolulu"], r["hawaii"], r["kauai"], r["maui"]]
        rep.expect(kids.get(r["year"]) == want, f"{SRC}.child_poverty_pct.{r['year']}", SRC, "transcription",
                   f"child poverty % {r['year']} match page 13", expected=kids.get(r["year"]), actual=want, location="p13")
    fpl = pj.get("hawaii_federal_poverty_guidelines_2025", {})
    g = section(p12, "Persons in Family or", "Comparison of Hawaii")
    for n, amt in fpl.get("persons", {}).items():
        m = re.search(rf"(?<!\d){n} \$[\d,]+ \$[\d,]+ \$([\d,]+)", g)
        got = int(m.group(1).replace(",", "")) if m else None
        rep.expect(got == amt, f"{SRC}.fpl_hawaii.{n}", SRC, "transcription",
                   f"Hawaiʻi poverty guideline, household of {n}", expected=got, actual=amt, location="p12")
