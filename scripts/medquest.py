"""
Med-QUEST — standalone, highly visible.

Enrollment by island from DHS Databook 2025, page 27.
SFY 2015 through SFY 2025. Figures as of June for each fiscal year.

This is island enrollment, not legislative-district enrollment,
and not an eligible-but-not-enrolled gap.

Unique filter: S2701 uninsured rate by district. A higher uninsured
rate may mean more Med-QUEST-eligible residents who are not enrolled.
Front-end agnostic. No UI imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from snap_gap import _load, _district_number, _num

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
S2701 = {
    "senate": RAW / "S2701_senate_districts.json",
    "house": RAW / "S2701_house_districts.json",
}

# DHS Databook 2025, page 27. Number of recipients by island.
ENROLLMENT = [
    {"sfy": 2015, "statewide": 332197, "oahu": 201668, "hawaii": 69975, "maui": 36597, "kauai": 19661, "molokai": 3521, "lanai": 775},
    {"sfy": 2016, "statewide": 346398, "oahu": 210743, "hawaii": 72591, "maui": 38092, "kauai": 20462, "molokai": 3685, "lanai": 826},
    {"sfy": 2017, "statewide": 356787, "oahu": 217155, "hawaii": 74108, "maui": 39618, "kauai": 21288, "molokai": 3777, "lanai": 842},
    {"sfy": 2018, "statewide": 359225, "oahu": 217942, "hawaii": 75258, "maui": 39895, "kauai": 21459, "molokai": 3824, "lanai": 848},
    {"sfy": 2019, "statewide": 345231, "oahu": 208864, "hawaii": 73452, "maui": 37832, "kauai": 20534, "molokai": 3764, "lanai": 787},
    {"sfy": 2020, "statewide": 361912, "oahu": 218283, "hawaii": 76304, "maui": 40726, "kauai": 21889, "molokai": 3896, "lanai": 814},
    {"sfy": 2021, "statewide": 428580, "oahu": 259838, "hawaii": 87650, "maui": 49972, "kauai": 26070, "molokai": 4116, "lanai": 934},
    {"sfy": 2022, "statewide": 460742, "oahu": 280585, "hawaii": 94191, "maui": 53214, "kauai": 27529, "molokai": 4217, "lanai": 1006},
    {"sfy": 2023, "statewide": 464153, "oahu": 283734, "hawaii": 94632, "maui": 53137, "kauai": 27494, "molokai": 4164, "lanai": 992},
    {"sfy": 2024, "statewide": 442537, "oahu": 265566, "hawaii": 91035, "maui": 55357, "kauai": 25440, "molokai": 4152, "lanai": 987},
    {"sfy": 2025, "statewide": 404922, "oahu": 244167, "hawaii": 85322, "maui": 47691, "kauai": 22964, "molokai": 3881, "lanai": 897},
]

ISLANDS = ["oahu", "hawaii", "maui", "kauai", "molokai", "lanai"]


def get_medquest(sfy: int = 2025, island: str | None = None) -> dict[str, Any]:
    """
    Med-QUEST enrollment.

    sfy: fiscal year 2015-2025. Default 2025 (latest).
    island: one of oahu, hawaii, maui, kauai, molokai, lanai, or None for all.
    """
    row = next((r for r in ENROLLMENT if r["sfy"] == sfy), None)
    if not row:
        return {"data_available": False, "error": "sfy must be 2015-2025"}

    islands = {}
    for name in ISLANDS:
        islands[name] = {
            "recipients": row[name],
            "share_of_state_percent": round(100 * row[name] / row["statewide"], 1),
        }

    result = {
        "data_available": True,
        "capability": "medquest",
        "program": "Med-QUEST",
        "title": "Med-QUEST enrollment by island",
        "sfy": sfy,
        "statewide": row["statewide"],
        "islands": islands,
        "source": "DHS Databook 2025, page 27. Figures as of June.",
        "how_to_display": "Own card, highly visible. Separate from SNAP, TANF, GA, and AABD.",
        "caveats": [
            "Island enrollment, not legislative-district enrollment.",
            "Not an eligible-but-not-enrolled gap.",
        ],
    }
    if island:
        key = island.lower()
        if key not in islands:
            return {"data_available": False, "error": f"island must be one of {ISLANDS}"}
        result["selected_island"] = key
        result["selected"] = islands[key]
    return result


def get_medquest_trend(island: str = "statewide") -> dict[str, Any]:
    """Enrollment for one island (or statewide) across SFY 2015-2025."""
    key = island.lower()
    if key not in ["statewide", *ISLANDS]:
        return {"data_available": False, "error": "unknown island"}
    series = [{"sfy": r["sfy"], "recipients": r[key]} for r in ENROLLMENT]
    return {
        "data_available": True,
        "capability": "medquest_trend",
        "program": "Med-QUEST",
        "island": key,
        "series": series,
        "source": "DHS Databook 2025, page 27",
    }


def get_medquest_uninsured(chamber: str, district_number: int) -> dict[str, Any]:
    """
    Unique Med-QUEST filter: uninsured rate by legislative district.

    Higher uninsured rate may mean more Med-QUEST-eligible residents
    who are not enrolled. This is a proxy, not a measured gap.
    """
    chamber = chamber.lower()
    if chamber not in S2701:
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    header, rows = _load(S2701[chamber])
    name_idx = header.index("NAME")
    row = next(
        ({header[i]: r[i] for i in range(len(header))}
         for r in rows if _district_number(r[name_idx]) == district_number),
        None,
    )
    if not row:
        return {"data_available": False, "chamber": chamber, "district": district_number,
                "error": "District not found in S2701."}

    total = _num(row.get("S2701_C01_001E"))
    insured = _num(row.get("S2701_C02_001E"))
    uninsured = _num(row.get("S2701_C04_001E"))
    uninsured_rate = _num(row.get("S2701_C05_001E"))
    insured_rate = _num(row.get("S2701_C03_001E"))

    return {
        "data_available": True,
        "capability": "medquest_uninsured",
        "program": "Med-QUEST",
        "filter": "uninsured",
        "title": "Uninsured rate",
        "chamber": chamber,
        "district": district_number,
        "uninsured_rate_percent": uninsured_rate,
        "uninsured_count": uninsured,
        "insured_rate_percent": insured_rate,
        "insured_count": insured,
        "civilian_population": total,
        "source": "S2701 C05_001E (percent uninsured), C04_001E (count)",
        "interpretation": "A higher uninsured rate may mean more Med-QUEST-eligible residents who are not enrolled.",
        "how_to_display": "Own filter on the Med-QUEST card. Unique to this program.",
        "caveats": [
            "Proxy only. Uninsured is not the same as Med-QUEST-eligible.",
            "Not a measured eligible-but-not-enrolled gap.",
            "Enrollment by island is a separate figure and is not by district.",
        ],
    }


def search_medquest_uninsured(chamber: str | None = None) -> list[dict[str, Any]]:
    """All districts ranked by uninsured rate, highest first."""
    chambers = [chamber.lower()] if chamber else ["senate", "house"]
    out = []
    for ch in chambers:
        header, rows = _load(S2701[ch])
        name_idx = header.index("NAME")
        for row in rows:
            num = _district_number(row[name_idx])
            if num is None:
                continue
            out.append(get_medquest_uninsured(ch, num))
    out.sort(key=lambda r: r.get("uninsured_rate_percent") or 0, reverse=True)
    return out
