"""
TANF demographic under-enrollment — standalone metric.

Compares the statewide DHS TANF race profile to the district-level
poverty demographic profile from Census S1701.

under_enrollment_pp = district share of people below poverty
                    − statewide share of TANF recipients

Positive means the group is a larger share of the district's poverty
population than of statewide TANF recipients: under-enrollment relative
to need. Negative means the reverse.

This is an indirect comparison. DHS demographics are statewide percentages,
not district enrollment. Race categories do not match Census categories
exactly (see GROUP_NOTES). Front-end agnostic. No UI imports.
"""

from __future__ import annotations

from typing import Any

from snap_gap import _load, _district_number, _num

# Statewide TANF race profile, DHS Databook 2025, June 2025 snapshot (page 8)
TANF_STATEWIDE = {
    "hawaiian": 33,
    "caucasian": 26,
    "other_pacific_islander": 21,
    "filipino": 8,
    "other_asian": 6,
    "black": 3,
    "aian": 1,
}

# Census S1701 below-poverty person counts by race
# Mapping is approximate. See GROUP_NOTES.
GROUPS = [
    {
        "key": "nhpi",
        "label": "Native Hawaiian / Pacific Islander alone",
        "tanf_keys": ["hawaiian", "other_pacific_islander"],
        "tanf_share": 33 + 21,  # DHS splits these; Census combines them
        "s1701_col": "S1701_C02_017E",
        "note": "DHS reports Hawaiian/part-Hawaiian (33%) and Other Pacific Islander (21%) separately. Census NHPI alone combines them and excludes part-Hawaiian in two-or-more races.",
    },
    {
        "key": "white",
        "label": "White alone",
        "tanf_keys": ["caucasian"],
        "tanf_share": 26,
        "s1701_col": "S1701_C02_013E",
        "note": "DHS Caucasian compared to Census White alone.",
    },
    {
        "key": "asian",
        "label": "Asian alone",
        "tanf_keys": ["filipino", "other_asian"],
        "tanf_share": 8 + 6,
        "s1701_col": "S1701_C02_016E",
        "note": "DHS Filipino (8%) plus Other Asian (6%) compared to Census Asian alone.",
    },
    {
        "key": "black",
        "label": "Black alone",
        "tanf_keys": ["black"],
        "tanf_share": 3,
        "s1701_col": "S1701_C02_014E",
        "note": "Direct comparison.",
    },
    {
        "key": "aian",
        "label": "American Indian / Alaska Native alone",
        "tanf_keys": ["aian"],
        "tanf_share": 1,
        "s1701_col": "S1701_C02_015E",
        "note": "Direct comparison. Small counts; wide margins.",
    },
]

FILES = {
    "senate": "S1701_senate_districts.json",
    "house": "S1701_house_districts.json",
}


def _paths():
    from pathlib import Path
    raw = Path(__file__).resolve().parent.parent / "data" / "raw"
    return {ch: raw / name for ch, name in FILES.items()}


def get_tanf_underenrollment(chamber: str, district_number: int) -> dict[str, Any]:
    """Under-enrollment metric for one district, by race group."""
    chamber = chamber.lower()
    paths = _paths()
    if chamber not in paths:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    header, rows = _load(paths[chamber])
    name_idx = header.index("NAME")
    row = next(
        ({header[i]: r[i] for i in range(len(header))}
         for r in rows if _district_number(r[name_idx]) == district_number),
        None,
    )
    if not row:
        return {"data_available": False, "chamber": chamber, "district": district_number,
                "error": "District not found in S1701."}

    total_poverty = _num(row.get("S1701_C02_001E"))
    groups = []
    for g in GROUPS:
        count = _num(row.get(g["s1701_col"]))
        share = round(100 * count / total_poverty, 1) if count is not None and total_poverty else None
        under = round(share - g["tanf_share"], 1) if share is not None else None
        # Also compare to the DHS Hawaiian/part-Hawaiian figure alone (33%),
        # which is the comparison in the worked example.
        hawaiian_only = 33 if g["key"] == "nhpi" else None
        under_vs_hawaiian = round(share - hawaiian_only, 1) if share is not None and hawaiian_only else None
        groups.append({
            "group": g["key"],
            "label": g["label"],
            "poverty_count": count,
            "district_poverty_share_percent": share,
            "statewide_tanf_share_percent": g["tanf_share"],
            "under_enrollment_pp": under,
            "under_enrolled": under is not None and under > 0,
            "hawaiian_only_tanf_share_percent": hawaiian_only,
            "under_enrollment_vs_hawaiian_only_pp": under_vs_hawaiian,
            "note": g["note"],
        })

    groups.sort(key=lambda x: x["under_enrollment_pp"] or 0, reverse=True)
    return {
        "data_available": True,
        "capability": "tanf_underenrollment",
        "title": "TANF under-enrollment by race",
        "chamber": chamber,
        "district": district_number,
        "poverty_population": total_poverty,
        "groups": groups,
        "largest_under_enrollment": groups[0]["label"] if groups else None,
        "method": "district poverty share minus statewide TANF share, in percentage points",
        "caveats": [
            "Indirect comparison. DHS TANF demographics are statewide, not by district.",
            "Positive under_enrollment_pp means the group is a larger share of district poverty than of statewide TANF recipients.",
            "Race categories do not match exactly between DHS and Census. See each group's note.",
            "Counts only from S1701 C02. Shares are computed from those counts.",
        ],
        "how_to_display": "Show as its own card. Lead with the under_enrollment_pp metric.",
    }


def search_tanf_underenrollment(chamber: str | None = None, group: str = "nhpi") -> list[dict[str, Any]]:
    """All districts, ranked by under-enrollment for one group."""
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        paths = _paths()
        header, rows = _load(paths[ch])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            result = get_tanf_underenrollment(ch, num)
            match = next((g for g in result["groups"] if g["group"] == group), None)
            if match:
                out.append({
                    "chamber": ch,
                    "district": num,
                    "group": group,
                    "under_enrollment_pp": match["under_enrollment_pp"],
                    "district_poverty_share_percent": match["district_poverty_share_percent"],
                    "statewide_tanf_share_percent": match["statewide_tanf_share_percent"],
                })
    out.sort(key=lambda r: r["under_enrollment_pp"] or 0, reverse=True)
    return out
