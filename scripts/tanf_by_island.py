"""
SNAP cases with TANF by island — standalone, front-end facing.

The BESSD workbook is a SNAP monthly summary. Its ``tanf`` column is SNAP persons/cases
with a TANF assistance category, not the full TANF caseload. This module keeps the island
context but labels it as SNAP-category context so it is not mistaken for TANF enrollment.

This is its own capability. Call get_tanf_by_island() and render the result.
No UI imports. Returns a plain dict.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BESSD = ROOT / "data" / "processed" / "bessd_sfy2026_caseload_by_island.csv"
POVERTY = ROOT / "data" / "processed" / "dhs_databook_census_poverty_estimates.json"

# July 2025 county population from the project county_housing table
POPULATION = {
    "OAHU": 988703,
    "HAWAII": 210043,
    "KAUAI": 73400,
    "MAUI": 160674,
}

# 2024 ACS poverty rate by county (S1701, reprinted in DHS Databook)
POVERTY_RATE_2024 = {
    "OAHU": 8.8,
    "HAWAII": 16.7,
    "KAUAI": 7.4,
    "MAUI": 9.7,
}

ISLANDS = [
    ("OAHU", "OB", "Honolulu County"),
    ("HAWAII", "HB", "Hawaii County"),
    ("KAUAI", "KB", "Kauai County"),
    ("MAUI", "MB", "Maui County"),
]


def get_tanf_by_island(month: str = "2026-02") -> dict[str, Any]:
    """
    Standalone TANF-by-island summary for the front end.

    Returns caseload, per-capita rate (per 1,000 residents), county poverty
    rate, and a simple comparison flag for each island.
    """
    rows = list(csv.DictReader(BESSD.open()))
    persons = {
        r["code"]: r
        for r in rows
        if r["month"] == month and r["metric"] == "persons"
    }

    islands = []
    for name, code, county in ISLANDS:
        rec = persons.get(code, {})
        tanf = float(rec["tanf"]) if rec.get("tanf") else None
        pop = POPULATION[name]
        poverty = POVERTY_RATE_2024[name]
        per_1000 = round(1000 * tanf / pop, 2) if tanf is not None else None
        # Higher per-capita enrollment relative to poverty is a rough uptake signal
        islands.append({
            "island": name,
            "county": county,
            "bessd_branch": code,
            "tanf_persons": tanf,
            "population": pop,
            "tanf_per_1000": per_1000,
            "poverty_rate_percent": poverty,
            "poverty_source": "ACS S1701 2024, county level (DHS Databook)",
        })

    # Rank so the front end can highlight without extra logic
    by_rate = sorted(islands, key=lambda r: r["tanf_per_1000"] or 0, reverse=True)
    by_poverty = sorted(islands, key=lambda r: r["poverty_rate_percent"], reverse=True)

    return {
        "capability": "tanf_by_island",
        "title": "SNAP cases with TANF category by island",
        "month": month,
        "source_caseload": "BESSD SFY 2026 monthly summary",
        "source_poverty": "ACS S1701 county poverty rate, 2024",
        "islands": islands,
        "highest_tanf_per_capita": by_rate[0]["island"] if by_rate else None,
        "highest_poverty_rate": by_poverty[0]["island"] if by_poverty else None,
        "note": (
            "Per-capita rate is SNAP persons with TANF category per 1,000 residents. "
            "Poverty rate is the county percent below poverty. "
            "These are island/county SNAP-category figures, not standalone TANF enrollment. "
            "Use DHS Databook SFY2025 (6,724 TANF/TAONF clients) for TANF caseload."
        ),
        "how_to_display": "Show as its own card or section. Do not nest under SNAP.",
    }
