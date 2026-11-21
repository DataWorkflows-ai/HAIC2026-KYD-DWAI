"""
TANF/TAONF eligibility proxy — front-end agnostic.

Searchable query: children under 18 below 50% of poverty, by legislative
district. This is a conservative public proxy for the deep-poverty child
population TANF/TAONF may reach.

Source: ACS B17024
  E003 + E016 + E029 = children under 18 below 50% of poverty

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
    "senate": RAW / "B17024_senate_districts.json",
    "house": RAW / "B17024_house_districts.json",
}

DEEP_POVERTY_CHILDREN = ("B17024_003", "B17024_016", "B17024_029")
UNDER_18_TOTAL = ("B17024_002", "B17024_015", "B17024_028")

CAVEATS = [
    "Eligibility proxy only. Counts children under 18 below 50% of Census poverty.",
    "Hawaii TANF/TAONF eligibility also depends on household composition, citizenship, assets, and work rules.",
    "This is not an enrollment count. Official TANF eligible counts are not published.",
    "All figures are ACS sample estimates and carry margins of error.",
]


def _row(chamber: str, number: int) -> dict[str, Any] | None:
    header, rows = _load(FILES[chamber])
    name_idx = header.index("NAME") if "NAME" in header else None
    geo_idx = header.index("GEO_ID") if "GEO_ID" in header else None
    for row in rows:
        n = _district_number(row[name_idx]) if name_idx is not None else int(str(row[geo_idx])[-3:]) if geo_idx is not None else None
        if n == number:
            return {header[i]: row[i] for i in range(len(header))}
    return None


def _em(row: dict[str, Any], col: str) -> tuple[float, float]:
    e_key, m_key = col + "E", col + "M"
    if e_key not in row:
        prefix, _, suffix = col.rpartition("_")
        e_key, m_key = f"{prefix}_E{suffix}", f"{prefix}_M{suffix}"
    return _num(row.get(e_key)) or 0, _num(row.get(m_key)) or 0


def get_tanf_proxy(chamber: str, district_number: int) -> dict[str, Any]:
    """Return the TANF eligibility proxy for one district."""
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    row = _row(chamber, district_number)
    if not row:
        return {"data_available": False, "chamber": chamber, "district": district_number,
                "error": "District not found in S1701."}

    vals = [_em(row, c) for c in DEEP_POVERTY_CHILDREN]
    total_vals = [_em(row, c)[0] for c in UNDER_18_TOTAL]
    related_below = sum(v for v, _ in vals)
    related_moe = sum(m ** 2 for _, m in vals) ** 0.5
    related_total = sum(total_vals)
    rate = None
    if related_below is not None and related_total:
        rate = round(100 * related_below / related_total, 1)

    return {
        "data_available": True,
        "program": "TANF/TAONF",
        "query": "children_under_18_below_50pct_poverty",
        "chamber": chamber,
        "district": district_number,
        "eligible_proxy": {
            "count": related_below,
            "moe": round(related_moe),
            "unit": "children under 18 below 50% poverty",
            "source": "B17024 E003+E016+E029",
            "year": "ACS 2020-2024",
        },
        "context": {
            "children_under_18_total": related_total,
            "children_under_18_total_source": "B17024 age totals",
            "percent_of_children_under_18_below_50pct_poverty": rate,
        },
        "citations": ["ACS B17024 2020-2024, E003+E016+E029 (children under 18 below 50% poverty)"],
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
        name_idx = header.index("NAME") if "NAME" in header else None
        geo_idx = header.index("GEO_ID") if "GEO_ID" in header else None
        for row in rows:
            num = _district_number(row[name_idx]) if name_idx is not None else int(str(row[geo_idx])[-3:]) if geo_idx is not None else None
            if num is None:
                continue
            result = get_tanf_proxy(ch, num)
            count = result.get("eligible_proxy", {}).get("count")
            if min_count is not None and (count is None or count < min_count):
                continue
            out.append(result)
    out.sort(key=lambda r: (r.get("eligible_proxy") or {}).get("count") or 0, reverse=True)
    return out
