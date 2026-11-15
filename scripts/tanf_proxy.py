"""
TANF/TAONF eligibility proxy — front-end agnostic.

Searchable query: related children under 18 below the poverty level,
by legislative district. This is the best public approximation of families
with related children who may be income-eligible for TANF/TAONF.

Source: ACS S1701
  C02_005E = Below poverty level, related children of householder under 18
  C01_005E = Total related children of householder under 18
  C02_002E = Below poverty level, all persons under 18

Counts only. No percent columns used in the result math.
No Streamlit or other UI imports. Returns a dict any front end can render.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from snap_gap import _load, _district_number, _num

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

FILES = {
    "senate": RAW / "S1701_senate_districts.json",
    "house": RAW / "S1701_house_districts.json",
}

RELATED_CHILDREN_BELOW_POVERTY = "S1701_C02_005E"
RELATED_CHILDREN_BELOW_POVERTY_MOE = "S1701_C02_005M"
RELATED_CHILDREN_TOTAL = "S1701_C01_005E"
UNDER_18_BELOW_POVERTY = "S1701_C02_002E"

CAVEATS = [
    "Eligibility proxy only. Counts related children under 18 below the poverty level.",
    "TANF/TAONF eligibility also depends on household composition, citizenship, assets, and work rules.",
    "This is not an enrollment count. DHS TANF demographics are statewide only.",
    "All figures are ACS sample estimates and carry margins of error.",
]


def _row(chamber: str, number: int) -> dict[str, Any] | None:
    header, rows = _load(FILES[chamber])
    name_idx = header.index("NAME")
    for row in rows:
        if _district_number(row[name_idx]) == number:
            return {header[i]: row[i] for i in range(len(header))}
    return None


def get_tanf_proxy(chamber: str, district_number: int) -> dict[str, Any]:
    """Return the TANF eligibility proxy for one district."""
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    row = _row(chamber, district_number)
    if not row:
        return {"data_available": False, "chamber": chamber, "district": district_number,
                "error": "District not found in S1701."}

    related_below = _num(row.get(RELATED_CHILDREN_BELOW_POVERTY))
    related_total = _num(row.get(RELATED_CHILDREN_TOTAL))
    under18_below = _num(row.get(UNDER_18_BELOW_POVERTY))
    rate = None
    if related_below is not None and related_total:
        rate = round(100 * related_below / related_total, 1)

    return {
        "data_available": True,
        "program": "TANF/TAONF",
        "query": "related_children_under_18_below_poverty",
        "chamber": chamber,
        "district": district_number,
        "eligible_proxy": {
            "count": related_below,
            "moe": _num(row.get(RELATED_CHILDREN_BELOW_POVERTY_MOE)),
            "unit": "related children under 18 below poverty",
            "source": "S1701 C02_005E",
            "year": "ACS 2020-2024",
        },
        "context": {
            "related_children_total": related_total,
            "related_children_total_source": "S1701 C01_005E",
            "percent_of_related_children_below_poverty": rate,
            "all_under_18_below_poverty": under18_below,
            "all_under_18_below_poverty_source": "S1701 C02_002E",
        },
        "citations": ["ACS S1701 2020-2024, C02_005E (related children under 18 below poverty)"],
        "caveats": CAVEATS,
    }


def search_tanf_proxy(chamber: str | None = None, min_count: float | None = None) -> list[dict[str, Any]]:
    """
    Searchable query across districts.

    chamber: "house", "senate", or None for both
    min_count: only return districts where the proxy count is at least this
    """
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        if ch not in FILES:
            continue
        header, rows = _load(FILES[ch])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            result = get_tanf_proxy(ch, num)
            count = result.get("eligible_proxy", {}).get("count")
            if min_count is not None and (count is None or count < min_count):
                continue
            out.append(result)
    out.sort(key=lambda r: (r.get("eligible_proxy") or {}).get("count") or 0, reverse=True)
    return out
