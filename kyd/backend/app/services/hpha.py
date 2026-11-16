"""HPHA public housing properties located in each 2022 district.

Input: data/raw/research/hpha/hpha_properties.csv: HPHA's public-housing inventory (85 properties, 86 rows), each
placed in a House and Senate district by point-in-polygon of HPHA's own map pins (an inference; see
hpha_unit_count_reconciliation.md). This is a *where are the developments* list. District statistics for federal
public housing stay on HUD's Picture of Subsidized Households (4,727 units, Dec 2025); HPHA's inventory totals differ
(5,008 itemized federal vs 5,406 published), and state-funded units (864) are not in HUD's data at all.
"""
from __future__ import annotations

import csv
from functools import lru_cache

from ..config import settings

URL = "https://hpha.hawaii.gov/programs-and-resources/public-housing"


@lru_cache
def _rows() -> list[dict]:
    p = settings().data_dir.parent.parent / "data" / "raw" / "research" / "hpha" / "hpha_properties.csv"
    if not p.exists():
        return []
    return list(csv.DictReader(p.open(encoding="utf-8")))


def properties(geo_id: str) -> dict:
    col = {"HD": "house_2022", "SD": "senate_2022"}.get(geo_id[:2])
    rows = _rows()
    if geo_id == "HI":
        mine = rows
    elif col:
        n = int(geo_id[3:])
        mine = [r for r in rows if r[col] and int(float(r[col])) == n]
    else:
        mine = []
    props = sorted(({"name": r["property_name"], "address": r["address"],
                     "city": r["location_city"], "island": r["island"], "type": r["property_type"],
                     "funding": r["funding_type"], "elderly": r["elderly"] == "Y",
                     "units": int(float(r["total_units"] or 0))} for r in mine), key=lambda p: -p["units"])
    return {"geo_id": geo_id, "properties": props,
            "units": sum(p["units"] for p in props),
            "state_units": sum(p["units"] for p in props if p["funding"] == "State"),
            "source": "Hawaiʻi Public Housing Authority, public housing inventory and property map", "url": URL,
            "caveats": ["Properties are placed in districts from HPHA's own map pins (point-in-polygon); grouped campuses share one pin.",
                        "Unit counts are HPHA's inventory table. Federal public-housing statistics elsewhere in the app use HUD's "
                        "Picture of Subsidized Households (4,727 units statewide, Dec 2025), which counts differently.",
                        "State-funded units (864 statewide) are HPHA-only; HUD's data does not include them."]}
