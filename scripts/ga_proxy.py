"""
General Assistance (GA) — standalone, separate from other programs.

Statewide snapshot from DHS Databook 2025, page 5 (June 2025).
District proxy from Census S1810: percent with a disability.
A higher district disability rate means more people likely GA-eligible.
GA serves temporarily disabled adults 18-64 without minor dependents.

S1801 was requested; it was not returned for Hawaii legislative districts
in this pull. S1810 supplies the same district disability rate.
Front-end agnostic. No UI imports.
"""

from __future__ import annotations

from typing import Any

from snap_gap import _load, _district_number, _num
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

FILES = {
    "senate": RAW / "S1810_senate_districts.json",
    "house": RAW / "S1810_house_districts.json",
}

# June 2025 statewide GA snapshot, DHS Databook 2025 page 5
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
    "citizenship": {
        "US Citizen": 90,
        "COFA": 7,
        "Non-US / Unspecified": 3,
    },
}


def get_ga_proxy(chamber: str, district_number: int) -> dict[str, Any]:
    """GA eligibility proxy for one district: disability rate from S1810."""
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    header, rows = _load(FILES[chamber])
    name_idx = header.index("NAME")
    row = next(
        ({header[i]: r[i] for i in range(len(header))}
         for r in rows if _district_number(r[name_idx]) == district_number),
        None,
    )
    if not row:
        return {"data_available": False, "chamber": chamber, "district": district_number,
                "error": "District not found in S1810."}

    with_disability = _num(row.get("S1810_C02_001E"))
    total_pop = _num(row.get("S1810_C01_001E"))
    # Prefer the published percent; fall back to count/total
    rate = _num(row.get("S1810_C03_001E"))
    if rate is None and with_disability is not None and total_pop:
        rate = round(100 * with_disability / total_pop, 1)

    return {
        "data_available": True,
        "capability": "ga_proxy",
        "program": "General Assistance",
        "title": "GA eligibility proxy",
        "chamber": chamber,
        "district": district_number,
        "disability_rate_percent": rate,
        "with_disability_count": with_disability,
        "civilian_population": total_pop,
        "source": "S1810 C03_001E (percent with a disability)",
        "interpretation": "A higher disability rate means more people likely eligible for GA.",
        "statewide_snapshot": GA_STATEWIDE,
        "caveats": [
            "Separate from SNAP, TANF, and other programs.",
            "Proxy only. GA also requires age 18-64, no minor dependents, and temporary disability.",
            "S1801 was not returned for these districts; S1810 supplies the disability rate.",
            "Statewide DHS demographics are not by district.",
        ],
        "how_to_display": "Show as its own card, separate from other programs.",
    }


def search_ga_proxy(chamber: str | None = None) -> list[dict[str, Any]]:
    """All districts, ranked by disability rate (highest likely GA need first)."""
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        header, rows = _load(FILES[ch])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            out.append(get_ga_proxy(ch, num))
    out.sort(key=lambda r: r.get("disability_rate_percent") or 0, reverse=True)
    return out
