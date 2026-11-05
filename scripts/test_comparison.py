"""Checks for district comparison. Run from repo root: python3 scripts/test_comparison.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.comparison import comparison_csv, rank_districts, uncertainty_flag


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return cond


def main():
    ok = True

    # Verified seniors-living-alone order, from the data, not hard-coded into the ranker
    ranked, missing = rank_districts("house", "householders_65plus_living_alone")
    top5 = [r["district"] for r in ranked[:5]]
    ok &= check("living alone top 5 is HD 28, 5, 23, 26, 27", top5 == [28, 5, 23, 26, 27])
    ok &= check("living alone has no missing rows", missing == 0)

    # Chamber separation
    senate, _ = rank_districts("senate", "householders_65plus_living_alone")
    ok &= check("senate ranking is not empty", len(senate) > 0)
    ok &= check("chambers are not mixed", all(r["chamber"] == "house" for r in ranked))
    ok &= check("senate rows are senate only", all(r["chamber"] == "senate" for r in senate))
    ok &= check("senate districts are 1-25", all(1 <= r["district"] <= 25 for r in senate))
    ok &= check("house districts are 1-51", all(1 <= r["district"] <= 51 for r in ranked))

    # Sorted highest first
    ok &= check(
        "house ranking is descending",
        all(ranked[i]["percent"] >= ranked[i + 1]["percent"] for i in range(len(ranked) - 1)),
    )

    # Missing is not zero
    ok &= check("missing flag is not zero", uncertainty_flag(None, 1) == "missing")
    ok &= check("zero estimate is flagged, not treated as missing", uncertainty_flag(0, 1).startswith("zero"))
    ok &= check("wide MOE is flagged", uncertainty_flag(10, 4) == "MOE exceeds 30% of estimate")
    ok &= check("narrow MOE is not flagged", uncertainty_flag(10, 2) == "")

    # CSV contents
    csv_text = comparison_csv(ranked)
    header = csv_text.splitlines()[0]
    for field in ["district", "percent", "percent_moe", "estimate", "denominator", "source_table", "year", "uncertainty_flag"]:
        ok &= check(f"CSV has {field}", field in header)
    ok &= check("CSV has 51 data rows", len(csv_text.splitlines()) - 1 == 51)
    ok &= check("CSV source is DP02", "DP02" in csv_text)
    ok &= check("CSV year is ACS 2020-2024", "ACS 2020-2024 5-year" in csv_text)

    # Denominator is households, not seniors
    ok &= check(
        "living alone denominator is Total households",
        ranked[0]["denominator"] == "Total households",
    )

    print()
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
