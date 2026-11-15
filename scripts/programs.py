"""
Program registry — the five capabilities a legislator can query.

Any front end calls list_programs() and renders the result.
No UI imports. Filters are named so the UI can show them as controls.
"""

from __future__ import annotations

from typing import Any


def list_programs() -> dict[str, Any]:
    """Return the five programs and their filters, ready for a front end."""
    return {
        "title": "Know Your District — program eligibility",
        "note": "Each program is its own capability. Filters are the controls inside it. Except for SNAP, these are eligibility proxies, not district enrollment and not a district gap.",
        "programs": [
            {
                "id": "snap",
                "name": "SNAP",
                "summary": "Enrolled vs eligible by district. The only program with a district-level gap.",
                "function": "get_snap_gap",
                "module": "scripts.snap_gap",
                "filters": [
                    {"id": "enrolled", "label": "SNAP households (count)", "source": "S2201 C03_001E"},
                    {"id": "eligible", "label": "People below 200% FPL", "source": "S1701 C01_042E"},
                    {"id": "gap", "label": "Eligible minus enrolled (counts)", "source": "computed"},
                    {"id": "person_level", "label": "SNAP persons estimate", "source": "S2201 count × DP02 average household size"},
                ],
            },
            {
                "id": "tanf",
                "name": "TANF / TAONF",
                "summary": "Families with related children under 18 below poverty, by district.",
                "function": "get_tanf_proxy",
                "module": "scripts.tanf_proxy",
                "filters": [
                    {"id": "related_children", "label": "Related children under 18 below poverty", "source": "S1701 C02_005E"},
                    {"id": "by_island", "label": "Caseload by island, per capita, vs county poverty", "source": "BESSD + S1701 county"},
                    {"id": "underenrollment", "label": "Race under-enrollment vs statewide DHS share", "source": "S1701 + DHS Databook"},
                ],
            },
            {
                "id": "ga",
                "name": "General Assistance",
                "summary": "Potential eligibility for temporarily disabled adults. One, two, or all three filters.",
                "function": "get_ga_proxy",
                "module": "scripts.ga_proxy",
                "filters": [
                    {"id": "disability", "label": "Disability rate", "source": "S1810"},
                    {"id": "poverty_18_64", "label": "Adults 18-64 below poverty", "source": "S1701 C02_006E"},
                    {"id": "age_structure", "label": "Working-age share (18-64)", "source": "DP05"},
                ],
            },
            {
                "id": "aabd",
                "name": "AABD",
                "summary": "Potential eligibility for aged, blind, and disabled. Each filter stands alone.",
                "function": "get_aabd",
                "module": "scripts.aabd",
                "filters": [
                    {"id": "disability", "label": "Disability prevalence", "source": "S1810"},
                    {"id": "age_65_plus", "label": "Population 65 and over (Senate only)", "source": "S0103 C02_001E"},
                    {"id": "foreign_born", "label": "Foreign-born, Oceania, year of entry", "source": "DP02"},
                ],
            },
            {
                "id": "medquest",
                "name": "Med-QUEST",
                "summary": "Island enrollment, plus uninsured rate by district as a potential-eligibility filter.",
                "function": "get_medquest",
                "module": "scripts.medquest",
                "filters": [
                    {"id": "enrollment", "label": "Enrollment by island (SFY 2015-2025)", "source": "DHS Databook page 27"},
                    {"id": "uninsured", "label": "Uninsured rate by district", "source": "S2701 C05_001E"},
                    {"id": "poverty", "label": "Income-eligible population (125/150/185/200% FPL)", "source": "S1701"},
                    {"id": "island_enrollment_to_need", "label": "Enrollment-to-need ratio by island", "source": "DHS enrollment / county S1701 poverty"},
                ],
            },
        ],
    }
