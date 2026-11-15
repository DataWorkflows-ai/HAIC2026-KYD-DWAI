"""
General Assistance (GA) — standalone, separate from other programs.

Three lenses the user can turn on one, two, or all three:

  disability     S1810 percent with a disability
  poverty_18_64  S1701 adults 18-64 below poverty
  age_structure  DP05 working-age share (18-64)

A district with a higher disability rate, more adults 18-64 in poverty,
or a larger working-age share has a larger likely GA-eligible population.

Statewide snapshot from DHS Databook 2025, page 5.
Front-end agnostic. No UI imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from snap_gap import _load, _district_number, _num

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

FILES = {
    "senate": {
        "s1810": RAW / "S1810_senate_districts.json",
        "s1701": RAW / "S1701_senate_districts.json",
        "dp05": RAW / "DP05_senate_districts.json",
    },
    "house": {
        "s1810": RAW / "S1810_house_districts.json",
        "s1701": RAW / "S1701_house_districts.json",
        "dp05": RAW / "DP05_house_districts.json",
    },
}

ALL_LENSES = ("disability", "poverty_18_64", "age_structure")

GA_STATEWIDE = {
    "snapshot": "June 2025",
    "sfy_2025_avg_monthly_clients": 4432,
    "sfy_2025_avg_monthly_cases": 4367,
    "sfy_2025_total_benefits": 20828507,
    "sex": {"Female": 41, "Male": 59},
    "age": {"18-39": 30, "40-64": 69, "65-79+": 0},
    "race_ethnicity": {
        "Caucasian": 35,
        "Hawaiian/part-Hawaiian": 28,
        "Other Pacific Islander": 13,
        "Filipino": 11,
        "Other Asian": 9,
        "Black": 4,
        "Other": 1,
    },
    "citizenship": {"US Citizen": 90, "COFA": 7, "Non-US / Unspecified": 3},
}


def _find(path: Path, number: int) -> dict[str, Any] | None:
    header, rows = _load(path)
    name_idx = header.index("NAME")
    for row in rows:
        if _district_number(row[name_idx]) == number:
            return {header[i]: row[i] for i in range(len(header))}
    return None


def _disability(row: dict) -> dict[str, Any]:
    count = _num(row.get("S1810_C02_001E"))
    total = _num(row.get("S1810_C01_001E"))
    rate = _num(row.get("S1810_C03_001E"))
    if rate is None and count is not None and total:
        rate = round(100 * count / total, 1)
    return {
        "lens": "disability",
        "label": "Disability rate",
        "rate_percent": rate,
        "count": count,
        "population": total,
        "source": "S1810 C03_001E",
        "interpretation": "Higher disability rate means more people likely GA-eligible.",
    }


def _poverty_18_64(row: dict) -> dict[str, Any]:
    below = _num(row.get("S1701_C02_006E"))
    total = _num(row.get("S1701_C01_006E"))
    rate = round(100 * below / total, 1) if below is not None and total else None
    return {
        "lens": "poverty_18_64",
        "label": "Adults 18-64 below poverty",
        "count": below,
        "population_18_64": total,
        "rate_percent": rate,
        "source": "S1701 C02_006E",
        "interpretation": "Adults 18-64 below poverty are the income side of GA eligibility.",
    }


def _age_structure(row: dict) -> dict[str, Any]:
    total = _num(row.get("DP05_0001E"))
    age_18_plus = _num(row.get("DP05_0021E"))
    age_65_plus = _num(row.get("DP05_0024E"))
    working = None
    if age_18_plus is not None and age_65_plus is not None:
        working = age_18_plus - age_65_plus
    share = round(100 * working / total, 1) if working is not None and total else None
    return {
        "lens": "age_structure",
        "label": "Working-age share (18-64)",
        "working_age_count": working,
        "total_population": total,
        "share_percent": share,
        "source": "DP05: 18 and over minus 65 and over",
        "interpretation": "A larger working-age share means a larger GA-eligible population.",
    }


def get_ga_proxy(
    chamber: str,
    district_number: int,
    lenses: list[str] | None = None,
) -> dict[str, Any]:
    """
    GA eligibility for one district.

    lenses: any of "disability", "poverty_18_64", "age_structure".
    None or empty means all three. Pass one or two to look at those only.
    """
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    wanted = list(lenses) if lenses else list(ALL_LENSES)
    bad = [x for x in wanted if x not in ALL_LENSES]
    if bad:
        return {"data_available": False, "error": f"unknown lenses: {bad}", "valid": list(ALL_LENSES)}

    result: dict[str, Any] = {
        "data_available": True,
        "capability": "ga_proxy",
        "program": "General Assistance",
        "title": "GA eligibility",
        "chamber": chamber,
        "district": district_number,
        "lenses_requested": wanted,
        "statewide_snapshot": GA_STATEWIDE,
        "how_to_display": "Own card. Show only the lenses requested. Can layer with other programs.",
    }

    if "disability" in wanted:
        row = _find(FILES[chamber]["s1810"], district_number)
        result["disability"] = _disability(row) if row else {"error": "not found"}
    if "poverty_18_64" in wanted:
        row = _find(FILES[chamber]["s1701"], district_number)
        result["poverty_18_64"] = _poverty_18_64(row) if row else {"error": "not found"}
    if "age_structure" in wanted:
        row = _find(FILES[chamber]["dp05"], district_number)
        result["age_structure"] = _age_structure(row) if row else {"error": "not found"}

    result["caveats"] = [
        "Separate from SNAP, TANF, AABD, and Med-QUEST.",
        "Proxy only. GA also requires temporary disability and no minor dependents.",
        "S1801 was not returned for these districts; S1810 supplies the disability rate.",
        "Working-age share is 18 and over minus 65 and over from DP05.",
    ]
    return result


def search_ga_proxy(chamber: str | None = None, lens: str = "disability") -> list[dict[str, Any]]:
    """All districts, ranked by one lens."""
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        header, rows = _load(FILES[ch]["s1810"])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            out.append(get_ga_proxy(ch, num, lenses=[lens]))
    key = {"disability": "rate_percent", "poverty_18_64": "rate_percent", "age_structure": "share_percent"}[lens]
    out.sort(key=lambda r: (r.get(lens) or {}).get(key) or 0, reverse=True)
    return out
