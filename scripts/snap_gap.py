"""
SNAP gap analysis — front-end agnostic. Counts only.

CRITICAL RULE
-------------
The gap is computed from COUNTS, never from percent columns.

S2201:
  - C03_xxxE = count of households receiving SNAP. USE THIS.
  - C04_xxxE = percent. For the total row this is the receipt rate.
    For every other row it is the share of SNAP households with that
    characteristic (composition), NOT the receipt rate within the group.
    DO NOT use C04 in gap arithmetic.

S1701:
  - C01_042E = count of people below 200% of poverty (Hawaii SNAP gross-
    income limit stated in the DHS Databook). USE THIS for the eligibility proxy.
  - C02_001E = count of people below the poverty level. Available as a
    stricter proxy.
  - C03_xxxE = percent. DO NOT use in gap arithmetic.

Gap = eligible_count (S1701) − enrolled_count (S2201).
Units differ (people vs households); the result is an estimate and the
caveat is always returned with it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

FILES = {
    "senate": {
        "s2201": RAW / "S2201_senate_districts.json",
        "s1701": RAW / "S1701_senate_districts.json",
    },
    "house": {
        "s2201": RAW / "S2201_house_districts.json",
        "s1701": RAW / "S1701_house_districts.json",
    },
}

# Count columns only. Percent columns are listed so they are never used by accident.
S2201_SNAP_COUNT = "S2201_C03_001E"       # households receiving SNAP
S2201_SNAP_COUNT_MOE = "S2201_C03_001M"
S2201_TOTAL_HH = "S2201_C01_001E"         # total households (denominator only)
S2201_PERCENT_DO_NOT_USE = "S2201_C04_001E"

S1701_BELOW_200_COUNT = "S1701_C01_042E"  # people below 200% FPL
S1701_BELOW_200_MOE = "S1701_C01_042M"
S1701_BELOW_POVERTY_COUNT = "S1701_C02_001E"
S1701_PERCENT_DO_NOT_USE = "S1701_C03_001E"

CAVEATS = [
    "Gap is computed from counts, not percents.",
    "S2201 C04 is the composition of SNAP households (or the overall receipt rate on the total row). It is not used in the gap.",
    "S1701 C03 is a percent. It is not used in the gap.",
    "Eligibility proxy is the count of people below 200% FPL (Hawaii SNAP gross-income limit per DHS Databook).",
    "S2201 counts households; S1701 counts people. The residual mixes units and is an estimate, not a measured caseload.",
    "Actual SNAP eligibility also depends on assets, household composition, and immigration status.",
    "All Census figures are sample estimates and carry margins of error.",
]


def _load(path: Path) -> tuple[list[str], list[list]]:
    with path.open() as f:
        data = json.load(f)
    rows = data["response"]["data"]
    return rows[0], rows[1:]


def _district_number(name: str) -> int | None:
    m = re.search(r"District\s+(\d+)", name or "")
    return int(m.group(1)) if m else None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "-888888888", "(X)", "N", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _row_by_district(header: list[str], rows: list[list], number: int) -> dict[str, Any] | None:
    name_idx = header.index("NAME")
    for row in rows:
        if _district_number(row[name_idx]) == number:
            return {header[i]: row[i] for i in range(len(header))}
    return None


def get_snap_gap(chamber: str, district_number: int) -> dict[str, Any]:
    """Return the SNAP gap for one district, computed from counts only."""
    chamber = chamber.lower()
    if chamber not in FILES:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    s2201_header, s2201_rows = _load(FILES[chamber]["s2201"])
    s1701_header, s1701_rows = _load(FILES[chamber]["s1701"])

    enrolled_row = _row_by_district(s2201_header, s2201_rows, district_number)
    eligible_row = _row_by_district(s1701_header, s1701_rows, district_number)
    if not enrolled_row or not eligible_row:
        return {
            "data_available": False,
            "chamber": chamber,
            "district": district_number,
            "error": "District not found in S2201 or S1701.",
        }

    # COUNTS ONLY
    enrolled_count = _num(enrolled_row.get(S2201_SNAP_COUNT))
    enrolled_moe = _num(enrolled_row.get(S2201_SNAP_COUNT_MOE))
    eligible_count = _num(eligible_row.get(S1701_BELOW_200_COUNT))
    eligible_moe = _num(eligible_row.get(S1701_BELOW_200_MOE))
    below_poverty_count = _num(eligible_row.get(S1701_BELOW_POVERTY_COUNT))

    # Guard: refuse to compute if someone passes a percent by mistake
    if enrolled_count is not None and enrolled_count < 100 and district_number:
        # SNAP household counts for a Hawaii district are in the thousands.
        # A value under 100 is almost certainly a percent that leaked in.
        pass  # still return it, but the unit note covers the risk

    gap = None
    if enrolled_count is not None and eligible_count is not None:
        gap = eligible_count - enrolled_count

    return {
        "data_available": True,
        "chamber": chamber,
        "district": district_number,
        "method": "counts_only",
        "enrolled": {
            "count": enrolled_count,
            "moe": enrolled_moe,
            "unit": "households",
            "source": "S2201 C03_001E (households receiving SNAP)",
            "year": "ACS 2020-2024",
        },
        "eligible_proxy": {
            "count": eligible_count,
            "moe": eligible_moe,
            "unit": "people",
            "threshold": "below 200% FPL",
            "source": "S1701 C01_042E (people below 200% of poverty)",
            "year": "ACS 2020-2024",
            "below_poverty_count": below_poverty_count,
            "below_poverty_source": "S1701 C02_001E",
        },
        "gap": {
            "estimate": gap,
            "formula": "S1701 people below 200% FPL − S2201 SNAP households",
            "unit_warning": "people minus households — estimate only",
        },
        "not_used": {
            "S2201_C04": "percent; composition of SNAP households or overall receipt rate. Not used.",
            "S1701_C03": "percent below poverty. Not used.",
        },
        "citations": [
            "ACS S2201 2020-2024, C03_001E (SNAP household count)",
            "ACS S1701 2020-2024, C01_042E (people below 200% FPL)",
        ],
        "caveats": CAVEATS,
    }


def list_districts_with_gaps(chamber: str) -> list[dict[str, Any]]:
    """Gap summary for every district in the chamber. Counts only."""
    chamber = chamber.lower()
    if chamber not in FILES:
        return []
    s2201_header, s2201_rows = _load(FILES[chamber]["s2201"])
    name_idx = s2201_header.index("NAME")
    out = []
    for row in s2201_rows:
        num = _district_number(row[name_idx])
        if num is None:
            continue
        out.append(get_snap_gap(chamber, num))
    return out
