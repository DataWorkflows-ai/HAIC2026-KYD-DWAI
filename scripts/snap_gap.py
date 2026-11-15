"""
SNAP gap analysis — front-end agnostic.

Reads S2201 (enrolled) and S1701 (income-eligible) data,
computes eligible-but-not-enrolled estimates, and returns
structured results any UI can render.

No Streamlit, Flask, or other web framework imports.
"""

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

S2201_SENATE = RAW / "S2201_senate_districts.json"
S2201_HOUSE = RAW / "S2201_house_districts.json"
S1701_SENATE = RAW / "S1701_senate_districts.json"
S1701_HOUSE = RAW / "S1701_house_districts.json"


def get_snap_gap(chamber: str, district_number: int) -> dict[str, Any]:
    """
    Return the SNAP enrolled-vs-eligible gap for one district.

    Parameters
    ----------
    chamber : "house" or "senate"
    district_number : int

    Returns
    -------
    dict with keys:
        district, chamber,
        enrolled (count, rate, moe, source, demographics),
        eligible_proxy (count, moe, source, demographics),
        gap (estimate, moe, caveats),
        demographic_comparison (list of group contrasts),
        citations (list),
        data_available (bool)
    """
    chamber = chamber.lower()
    if chamber not in ("house", "senate"):
        return {"data_available": False, "error": "chamber must be 'house' or 'senate'"}

    # TODO: replace this stub with real parsing of S2201 + S1701
    # and the gap calculation described in SNAP_Analytical_Framework.md
    return {
        "data_available": False,
        "district": district_number,
        "chamber": chamber,
        "message": "SNAP gap calculation not yet implemented. S2201 and S1701 files are present in data/raw/.",
        "enrolled": None,
        "eligible_proxy": None,
        "gap": None,
        "demographic_comparison": [],
        "citations": [
            "ACS S2201 2020-2024 (SNAP receipt by district)",
            "ACS S1701 2020-2024 (poverty / income-to-poverty by district)",
        ],
        "caveats": [
            "Eligible-but-not-enrolled is an estimate based on <130% FPL, not a measured caseload.",
            "Actual SNAP eligibility also depends on assets, household composition, and immigration status.",
            "All Census figures carry margins of error.",
        ],
    }


def list_districts_with_gaps(chamber: str) -> list[dict[str, Any]]:
    """
    Return gap summaries for every district in the chamber.
    Useful for maps and ranking views. Does not modify map configuration.
    """
    # TODO: implement once gap table exists
    return []
