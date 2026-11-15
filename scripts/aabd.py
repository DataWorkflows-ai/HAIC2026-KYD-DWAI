"""
AABD — Aid to the Aged, Blind, and Disabled. Standalone, highly visible.

Lenses the user can turn on separately:

  disability   S1810 percent with a disability (own filter for potential eligibility)
  age_65_plus  S0103 people 65 and over (Senate only)

Statewide snapshot from DHS Databook 2025, page 4.
Not district enrollment. Not an eligible-but-not-enrolled gap.
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
        "s0103": RAW / "S0103_senate_districts.json",
    },
    "house": {
        "s1810": RAW / "S1810_house_districts.json",
        "s0103": None,  # withheld for most House districts
    },
}

AABD_STATEWIDE = {
    "snapshot": "June 2025",
    "source": "DHS Databook 2025, page 4",
    "sfy_2025_avg_monthly_clients": 754,
    "sfy_2025_avg_monthly_cases": 677,
    "sfy_2025_total_benefits": 2823120,
    "sex": {"Female": 65, "Male": 35},
    "age": {"0-64": 8, "65-79": 72, "80+": 20},
    "race_ethnicity": {
        "Other Pacific Islander": 51,
        "Other Asian": 15,
        "Filipino": 14,
        "Caucasian": 12,
        "Hawaiian/part-Hawaiian": 6,
        "Black": 1,
    },
    "citizenship": {"COFA": 46, "US Citizen": 30, "Non-US / Unspecified": 24},
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
        "filter": "disability",
        "label": "Disability prevalence",
        "rate_percent": rate,
        "count": count,
        "population": total,
        "source": "S1810 C03_001E",
        "interpretation": "Own filter for AABD potential eligibility. Higher disability prevalence means more people who may meet the disability criterion.",
    }


def _age_65(row: dict) -> dict[str, Any]:
    count = _num(row.get("S0103_C02_001E"))
    return {
        "filter": "age_65_plus",
        "label": "Population 65 and over",
        "count": count,
        "source": "S0103 C02_001E",
        "senate_only": True,
        "interpretation": "Age side of AABD eligibility. More residents 65+ means a larger likely eligible population on the age criterion.",
    }


def get_aabd(
    chamber: str,
    district_number: int,
    filters: list[str] | None = None,
) -> dict[str, Any]:
    """
    AABD for one district.

    filters: "disability", "age_65_plus", or both.
    None means both where available. age_65_plus is Senate only.
    """
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    wanted = list(filters) if filters else ["disability", "age_65_plus"]
    result: dict[str, Any] = {
        "data_available": True,
        "capability": "aabd",
        "program": "AABD",
        "title": "AABD potential eligibility",
        "chamber": chamber,
        "district": district_number,
        "filters_requested": wanted,
        "statewide_snapshot": AABD_STATEWIDE,
        "how_to_display": "Own card, highly visible. Separate from SNAP, TANF, GA, and Med-QUEST.",
    }

    if "disability" in wanted:
        row = _find(FILES[chamber]["s1810"], district_number)
        result["disability"] = _disability(row) if row else {"error": "not found"}

    if "age_65_plus" in wanted:
        path = FILES[chamber]["s0103"]
        if path is None:
            result["age_65_plus"] = {
                "available": False,
                "reason": "S0103 is withheld for most House districts. Not zero.",
            }
        else:
            row = _find(path, district_number)
            result["age_65_plus"] = _age_65(row) if row else {"error": "not found"}

    result["caveats"] = [
        "Not district enrollment. Not an eligible-but-not-enrolled gap.",
        "Disability prevalence is its own filter for potential eligibility.",
        "65+ count is Senate only.",
        "Statewide DHS demographics are not by district.",
    ]
    return result


def search_aabd_disability(chamber: str | None = None) -> list[dict[str, Any]]:
    """All districts ranked by disability prevalence."""
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        header, rows = _load(FILES[ch]["s1810"])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            out.append(get_aabd(ch, num, filters=["disability"]))
    out.sort(key=lambda r: (r.get("disability") or {}).get("rate_percent") or 0, reverse=True)
    return out
