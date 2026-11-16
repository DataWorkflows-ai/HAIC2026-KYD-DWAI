"""Census API extracts in data/raw/*_districts.json (Crystal's program scripts read these).

A "format change" in Census data is usually silent: a variable code keeps its name but now means
something else, or moves. So besides structure, every code the scripts rely on is pinned by an
IDENTITY that only holds if the code still means what the scripts assume:

  percent column == count / total × 100     (C01/C02/C03 roles in S1701, S2201, S1810, S2701)
  subject-table rate == Data Profile rate   (S1701 vs DP03, S2201 vs DP03, S1810 vs DP02, S2701 vs DP03)
  poverty ladder is ordered                 (50% < 100% < 125% < 150% < 185% < 200% < total)
  Data Profile values == DBEDT workbook     (Crystal's DP JSON vs the xlsx that kyd.sqlite is built from)
"""
from __future__ import annotations
import json
import re
import sqlite3
from pathlib import Path

from core import RAW, REPO, Report, close, rel_close

TABLES = {  # table → chambers available
    "S1701": ("house", "senate"), "S2201": ("house", "senate"), "S1810": ("house", "senate"),
    "S2701": ("house", "senate"), "S0103": ("senate",), "DP02": ("house", "senate"),
    "DP03": ("house", "senate"), "DP05": ("house", "senate"),
}
N = {"house": 51, "senate": 25}
SENTINELS = {"-666666666", "-999999999", "-888888888", "-222222222", "-333333333", "-555555555"}
# Codes the program scripts depend on (scripts/snap_gap.py, tanf_*.py, ga_proxy.py, aabd.py, medquest.py).
USED = {
    "S1701": ["C01_001E", "C02_001E", "C03_001E", "C01_005E", "C02_005E", "C01_006E", "C02_002E", "C02_006E",
              "C01_038E", "C01_039E", "C01_040E", "C01_041E", "C01_042E", "C02_010E", "C02_013E", "C02_014E",
              "C02_015E", "C02_016E", "C02_017E"],
    "S2201": ["C01_001E", "C03_001E", "C04_001E"],
    "S1810": ["C01_001E", "C02_001E", "C03_001E"],
    "S2701": ["C01_001E", "C04_001E", "C05_001E"],
    "S0103": ["C01_001E", "C02_001E"],
    "DP02": ["DP02_0001E", "DP02_0016E", "DP02_0072PE"],
    "DP03": ["DP03_0074PE", "DP03_0099PE", "DP03_0128PE"],
    "DP05": ["DP05_0001E", "DP05_0024E"],
}


def code(table: str, c: str) -> str:
    return c if c.startswith(table) else f"{table}_{c}"


def load(table: str, chamber: str) -> tuple[dict, dict[int, dict]]:
    d = json.loads((RAW / f"{table}_{chamber}_districts.json").read_text())["response"]
    header, rows = d["data"][0], d["data"][1:]
    by = {}
    for r in rows:
        row = dict(zip(header, r))
        m = re.search(r"District\s+(\d+)", row.get("NAME") or "")
        if m:
            by[int(m.group(1))] = row
    return {k: v for k, v in d.items() if k != "data"} | {"header": header, "n_rows": len(rows)}, by


def num(v) -> float | None:
    if v is None or str(v).strip() in SENTINELS or str(v).strip() in ("", "(X)", "N", "null", "-"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def run(rep: Report) -> None:
    data: dict[tuple[str, str], dict[int, dict]] = {}

    # 1. structure: file present, expected table/vintage, one row per district, codes present, no sentinels
    for table, chambers in TABLES.items():
        for ch in chambers:
            src = f"census.{table}.{ch}"
            p = RAW / f"{table}_{ch}_districts.json"
            if not rep.expect(p.exists(), f"{src}.present", src, "format", f"{p.name} exists"):
                continue
            try:
                meta, rows = load(table, ch)
            except Exception as e:
                rep.add(f"{src}.parse", src, "format", "fail", f"cannot parse Census response: {e}")
                continue
            data[(table, ch)] = rows
            rep.expect(meta.get("tableName") == table, f"{src}.table", src, "format",
                       "response is for the expected table", expected=table, actual=meta.get("tableName"))
            year = re.search(r"/data/(\d{4})/acs/acs5", meta.get("dataAPIURI", ""))
            rep.expect(bool(year) and year.group(1) == "2024", f"{src}.vintage", src, "format",
                       "ACS 5-year 2020–2024 vintage", expected="2024", actual=year.group(1) if year else None)
            rep.expect(sorted(rows) == list(range(1, N[ch] + 1)), f"{src}.districts", src, "format",
                       f"one row for each of the {N[ch]} {ch} districts", expected=N[ch], actual=len(rows))
            missing = [c for c in USED[table] if code(table, c) not in meta["header"]]
            rep.expect(not missing, f"{src}.codes", src, "format", "every variable the scripts use is present",
                       actual=missing or None)
            bad = sorted({(d, c) for d, r in rows.items() for c in USED[table]
                          if code(table, c) in r and (str(r[code(table, c)]).strip() in SENTINELS
                                                      or num(r[code(table, c)]) is None)})
            rep.expect(not bad, f"{src}.values", src, "format", "used variables are numeric (no Census null codes)",
                       actual=[f"D{d}:{c}" for d, c in bad[:10]] or None,
                       fail_status="warn" if len(bad) <= 2 else "fail")

    def v(table, ch, d, c):
        return num(data.get((table, ch), {}).get(d, {}).get(code(table, c)))

    def per_district(id, src, kind, detail, chambers, fn, *, tol_fail_ratio=0.0):
        """fn(ch, d) → (ok, actual). Pass if every district passes."""
        for ch in chambers:
            bad = []
            for d in range(1, N[ch] + 1):
                ok, actual = fn(ch, d)
                if not ok:
                    bad.append(f"D{d}: {actual}")
            rep.expect(not bad, f"{id}.{ch}", f"{src}.{ch}", kind, detail, actual=bad[:8] or None,
                       location=f"{len(bad)} of {N[ch]} districts" if bad else None)

    pct = lambda a, b: None if a is None or not b else 100 * a / b

    # 2. internal identities: the C01/C02/C03 roles still mean count / total / percent
    for table, cnt, tot, rate in (("S1701", "C02_001E", "C01_001E", "C03_001E"),
                                  ("S2201", "C03_001E", "C01_001E", "C04_001E"),
                                  ("S1810", "C02_001E", "C01_001E", "C03_001E"),
                                  ("S2701", "C04_001E", "C01_001E", "C05_001E")):
        per_district(f"census.{table}.rate_identity", f"census.{table}", "consistency",
                     f"{rate} equals {cnt} / {tot} × 100 (column roles unchanged)", TABLES[table],
                     lambda ch, d, t=table, a=cnt, b=tot, r=rate: (
                         close(pct(v(t, ch, d, a), v(t, ch, d, b)), v(t, ch, d, r), 0.11),
                         f"{pct(v(t, ch, d, a), v(t, ch, d, b)) and round(pct(v(t, ch, d, a), v(t, ch, d, b)), 2)} vs {v(t, ch, d, r)}"))

    # 3. subject table vs Data Profile: same ACS estimate published twice
    for table, c, dp, dpc, what in (("S1701", "C03_001E", "DP03", "DP03_0128PE", "poverty rate"),
                                    ("S2201", "C04_001E", "DP03", "DP03_0074PE", "SNAP receipt rate"),
                                    ("S1810", "C03_001E", "DP02", "DP02_0072PE", "disability rate"),
                                    ("S2701", "C05_001E", "DP03", "DP03_0099PE", "uninsured rate"),
                                    ("S2201", "C01_001E", "DP02", "DP02_0001E", "total households")):
        tol = 0.11 if "P" in dpc[-3:] else 0.5
        per_district(f"census.{table}.vs_{dp}.{c}", f"census.{table}", "cross_source",
                     f"{table} {c} ({what}) matches {dpc}", TABLES[table],
                     lambda ch, d, t=table, c=c, dp=dp, dpc=dpc, tol=tol: (
                         close(v(t, ch, d, c), v(dp, ch, d, dpc), tol), f"{v(t, ch, d, c)} vs {v(dp, ch, d, dpc)}"))
    per_district("census.S0103.vs_DP05.65plus", "census.S0103", "cross_source",
                 "S0103 C02_001E (people 65+) matches DP05_0024E", ("senate",),
                 lambda ch, d: (rel_close(v("S0103", ch, d, "C02_001E"), v("DP05", ch, d, "DP05_0024E"), 0.005),
                                f"{v('S0103', ch, d, 'C02_001E')} vs {v('DP05', ch, d, 'DP05_0024E')}"))

    # 4. poverty ladder order: pins C01_038…042 to 50/125/150/185/200 % of poverty
    ladder = ["C01_038E", "C02_001E", "C01_039E", "C01_040E", "C01_041E", "C01_042E", "C01_001E"]
    per_district("census.S1701.poverty_ladder", "census.S1701", "consistency",
                 "people below 50% < 100% < 125% < 150% < 185% < 200% of poverty < all people", ("house", "senate"),
                 lambda ch, d: ((lambda xs: all(x is not None for x in xs) and all(a <= b for a, b in zip(xs, xs[1:])))(
                     [v("S1701", ch, d, c) for c in ladder]), [v("S1701", ch, d, c) for c in ladder]))

    # 5. House and Senate plans partition the same state
    for table, c in (("DP05", "DP05_0001E"), ("S1701", "C01_001E"), ("S2201", "C03_001E"), ("S1701", "C01_042E")):
        h = sum(v(table, "house", d, c) or 0 for d in range(1, 52))
        s = sum(v(table, "senate", d, c) or 0 for d in range(1, 26))
        rep.expect(rel_close(h, s, 0.01), f"census.{table}.{c}.house_eq_senate", f"census.{table}", "consistency",
                   f"{c} summed over House districts ≈ over Senate districts (same state)",
                   expected=round(h), actual=round(s), fail_status="warn")

    # 6. Crystal's DP JSON vs the DBEDT workbook behind kyd.sqlite (two independent publications)
    db = REPO / "kyd" / "data" / "kyd.sqlite"
    if db.exists():
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        inds = {r[0]: (r[1], r[2]) for r in con.execute("SELECT indicator, acs, unit FROM indicator")}
        obs = {(r[0], r[1]): r[2] for r in con.execute("SELECT geo_id, indicator, value FROM observation")}
        for ind, (acs, unit) in sorted(inds.items()):
            if not acs or not re.match(r"^DP0\d_\d{4}$", acs or ""):
                continue
            t = acs[:4]
            col = acs + ("PE" if unit == "pct" else "E")
            bad, n = [], 0
            for ch, pre in (("house", "HD"), ("senate", "SD")):
                for d in range(1, N[ch] + 1):
                    a, b = obs.get((f"{pre}-{d:02d}", ind)), v(t, ch, d, col)
                    if a is None or b is None:
                        continue
                    n += 1
                    if not close(a, b, 0.11 if unit == "pct" else max(0.5, abs(b) * 1e-6)):
                        bad.append(f"{pre}-{d:02d}: {a} vs {b}")
            if n:
                rep.expect(not bad, f"census.{t}.vs_dbedt.{ind}", f"census.{t}", "cross_source",
                           f"{col} ({ind}) equals the DBEDT workbook value used by the app",
                           actual=bad[:6] or None, location=f"{len(bad)} of {n} districts" if bad else None)
