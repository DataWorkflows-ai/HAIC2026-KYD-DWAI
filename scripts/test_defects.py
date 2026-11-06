"""Regression tests for the three confirmed defects.

Run from repo root:
    python3 scripts/test_defects.py

1. Rent burden is taken from the GRAPI section, not the earlier SMOCAPI
   (homeowner) bands. Checked against the DBEDT source workbooks.
2. Rent ranking uses the corrected GRAPI calculation and does not query a
   nonexistent rent_burden_percent column.
3. Opening a profile from the other chamber does not raise
   StreamlitWidgetAlreadyInstantiatedError.
"""

import math
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.agent import answer
from scripts.comparison import rank_districts

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
HOUSE_XLSX = RAW / "acs2024_5yr_house_hi.xlsx"
SENATE_XLSX = RAW / "acs2024_5yr_senate_hi.xlsx"

# Old homeowner (SMOCAPI with mortgage) values that the first-match bug returned.
# A correct extraction must not match these.
OLD_HOMEOWNER = {
    ("house", 19): ("7.5%", "28.4%"),
}


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


def grapi_from_source(path, district):
    """Read the two GRAPI percent bands for one district from the source workbook."""
    df = pd.read_excel(path, sheet_name="DP04", header=None)
    col = None
    for c in range(1, df.shape[1], 4):
        name = str(df.iloc[0, c])
        m = re.search(r"District\s+(\d+)", name)
        if m and int(m.group(1)) == district:
            col = c
            break
    if col is None:
        raise AssertionError(f"district {district} not in {path}")
    grapi_row = None
    for i in range(len(df)):
        if "GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME" in str(df.iloc[i, 0]):
            grapi_row = i
            break
    if grapi_row is None:
        raise AssertionError("GRAPI section missing")
    bands = []
    for i in range(grapi_row + 1, len(df)):
        lab = str(df.iloc[i, 0])
        if lab in ("30.0 to 34.9 percent", "35.0 percent or more"):
            bands.append((
                str(df.iloc[i, col + 2]),
                str(df.iloc[i, col + 3]),
            ))
            if len(bands) == 2:
                break
    return bands


def main():
    ok = True
    house = pd.read_csv(ROOT / "data" / "processed" / "house_districts.csv")
    senate = pd.read_csv(ROOT / "data" / "processed" / "senate_districts.csv")

    # --- 1. Source-based GRAPI checks for all 76 districts ---
    for chamber, frame, path, expected_n in (
        ("house", house, HOUSE_XLSX, 51),
        ("senate", senate, SENATE_XLSX, 25),
    ):
        ok &= check(f"{chamber} has {expected_n} districts", len(frame) == expected_n)
        mismatches = []
        for _, row in frame.iterrows():
            d = int(row["district"])
            source = grapi_from_source(path, d)
            got = (
                str(row["rent_30_to_34_9_percent"]),
                str(row["rent_30_to_34_9_percent_moe"]),
                str(row["rent_35_plus_percent"]),
                str(row["rent_35_plus_percent_moe"]),
            )
            want = (source[0][0], source[0][1], source[1][0], source[1][1])
            if got != want:
                mismatches.append((d, got, want))
        ok &= check(
            f"{chamber} GRAPI bands match source for all {expected_n} districts",
            not mismatches,
        )
        if mismatches:
            print(f"  first mismatches: {mismatches[:3]}")

    # Acceptance examples
    h19 = house[house.district == 19].iloc[0]
    h22 = house[house.district == 22].iloc[0]
    s12 = senate[senate.district == 12].iloc[0]
    ok &= check("HD19 is 7.3% ±3.4 and 48.1% ±9.8",
                h19.rent_30_to_34_9_percent == "7.3%" and h19.rent_30_to_34_9_percent_moe == "±3.4"
                and h19.rent_35_plus_percent == "48.1%" and h19.rent_35_plus_percent_moe == "±9.8")
    ok &= check("HD22 is 9.9% ±2.7 and 39.2% ±5.1",
                h22.rent_30_to_34_9_percent == "9.9%" and h22.rent_30_to_34_9_percent_moe == "±2.7"
                and h22.rent_35_plus_percent == "39.2%" and h22.rent_35_plus_percent_moe == "±5.1")
    ok &= check("SD12 is 8.8% ±1.8 and 47.0% ±3.0",
                s12.rent_30_to_34_9_percent == "8.8%" and s12.rent_30_to_34_9_percent_moe == "±1.8"
                and s12.rent_35_plus_percent == "47.0%" and s12.rent_35_plus_percent_moe == "±3.0")

    # Reject the old homeowner values
    old = OLD_HOMEOWNER[("house", 19)]
    ok &= check(
        "HD19 is not the old homeowner SMOCAPI values (7.5% / 28.4%)",
        (h19.rent_30_to_34_9_percent, h19.rent_35_plus_percent) != old,
    )

    # Combined figures used by cards, profiles, chat
    def combined(row):
        p1 = float(str(row.rent_30_to_34_9_percent).replace("%", ""))
        p2 = float(str(row.rent_35_plus_percent).replace("%", ""))
        m1 = float(str(row.rent_30_to_34_9_percent_moe).replace("±", ""))
        m2 = float(str(row.rent_35_plus_percent_moe).replace("±", ""))
        return p1 + p2, math.sqrt(m1 ** 2 + m2 ** 2)

    c19, m19 = combined(h19)
    c22, m22 = combined(h22)
    ok &= check(f"HD19 combined is 55.4% ±10.4 (got {c19:.1f} ±{m19:.1f})",
                abs(c19 - 55.4) < 0.05 and abs(m19 - 10.4) < 0.05)
    ok &= check(f"HD22 combined is 49.1% ±5.8 (got {c22:.1f} ±{m22:.1f})",
                abs(c22 - 49.1) < 0.05 and abs(m22 - 5.8) < 0.05)

    # Seniors-living-alone calculation is unchanged
    ok &= check("HD22 65+ living alone still 14.6%",
                h22.householders_65plus_living_alone_percent == "14.6%")

    # --- 2. Rent ranking uses the GRAPI calculation, no exception ---
    for q, chamber in (
        ("Which district has the highest rent burden?", "house"),
        ("Which Senate district has the highest rent burden?", "senate"),
    ):
        try:
            result = answer(q)
            errored = False
        except Exception as exc:
            result, errored = str(exc), True
        ok &= check(f"ranking '{q}' does not raise", not errored)
        ok &= check(f"ranking '{q}' returns a list", result and "Top 5" in result)
        ranked, _ = rank_districts(chamber, "rent_burden")
        top = ranked[0]
        ok &= check(
            f"{chamber} ranking top matches comparison (District {top['district']})",
            result and f"District {top['district']}" in result and top["percent_display"] in result,
        )

    # HD19 and HD22 chat answers use the corrected renter figures
    a19 = answer("What is the rent burden in HD 19?")
    a22 = answer("What is the rent burden in HD 22?")
    ok &= check("HD19 chat says 55.4%", "55.4%" in a19)
    ok &= check("HD22 chat says 49.1%", "49.1%" in a22)
    ok &= check("HD19 chat does not use the homeowner 7.5% band alone", "7.5%" not in a19)

    # --- 3. Cross-chamber Open profile ---
    from streamlit.testing.v1 import AppTest

    def open_profile(start_chamber, cmp_chamber, district):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
        at.run()
        at.session_state["profile_chamber"] = start_chamber
        at.session_state["profile_district"] = 1 if start_chamber == "House" else 1
        at.run()
        at.radio(key="cmp_chamber").set_value(cmp_chamber).run()
        at.selectbox(key="open_profile").set_value(district).run()
        # The Open profile button is the one with that exact label
        for btn in at.button:
            if btn.label == "Open profile":
                btn.click()
                break
        at.run()
        return at

    paths = [
        ("House", "House", 19),
        ("House", "Senate", 12),
        ("Senate", "Senate", 12),
        ("Senate", "House", 19),
    ]
    for start, cmp, dist in paths:
        try:
            at = open_profile(start, cmp, dist)
            exceptions = [e.value for e in at.exception] if at.exception else []
            title = ""
            for md in at.markdown:
                if f"{cmp} District {dist}" in str(md.value):
                    title = str(md.value)
                    break
            no_exc = not any("StreamlitWidgetAlreadyInstantiatedError" in str(e) for e in exceptions)
            ok &= check(
                f"Open profile {start}->{cmp} {dist}: no widget error",
                no_exc,
            )
            ok &= check(
                f"Open profile {start}->{cmp} {dist}: title shows {cmp} District {dist}",
                title != "",
            )
            sidebar_ok = at.session_state.get("profile_chamber") == cmp
            ok &= check(
                f"Open profile {start}->{cmp} {dist}: sidebar chamber is {cmp}",
                sidebar_ok,
            )
            if exceptions:
                print(f"  exceptions: {exceptions}")
        except Exception as exc:
            ok &= check(f"Open profile {start}->{cmp} {dist} ran", False)
            print(f"  raised: {type(exc).__name__}: {exc}")

    print()
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
