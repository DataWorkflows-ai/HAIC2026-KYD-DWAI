"""Generate SOURCES.md (repo root) from kyd/data/sources.csv, the list the app's Sources tab shows.

  python kyd/etl/make_sources_md.py
"""
import csv
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "kyd" / "data" / "sources.csv"
OUT = REPO / "SOURCES.md"


def build() -> str:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    groups: "OrderedDict[str, list]" = OrderedDict()
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    lines = ["# Sources", "",
             f"Every source Know Your District draws on ({len(rows)} in all). Generated from `kyd/data/sources.csv` "
             "by `kyd/etl/make_sources_md.py`; the app's Sources tab shows the same list. Figure-level citations "
             "(source, vintage, method, margin of error) travel with every number through the API.", ""]
    for g, rs in groups.items():
        lines += [f"## {g}", "", "| Source | Publisher | What it provides | Vintage | Used in | Accessed |",
                  "|---|---|---|---|---|---|"]
        for r in rs:
            cell = lambda k: r[k].replace("|", "\\|")
            lines.append(f"| [{cell('name')}]({r['url']}) | {cell('publisher')} | {cell('provides')} | "
                         f"{cell('vintage')} | {cell('used_in')} | {cell('accessed')} |")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return str(OUT)


if __name__ == "__main__":
    print(build())
