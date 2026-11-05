"""
District comparison for a single chamber and a single verified measure.

Ranks by percentage, highest first. Missing values are excluded and never
treated as zero. Does not create a composite need score or an enrollment gap.
"""

import csv
import io
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"
YEAR = "ACS 2020-2024 5-year"

# Programs whose official pages were opened. Checked dates are fixed strings,
# not computed when the app runs. Summaries restate only what those pages stated.
PROGRAMS = {
    "snap": {
        "name": "Supplemental Nutrition Assistance Program (SNAP)",
        "url": "https://humanservices.hawaii.gov/bessd/snap/",
        "checked": "2026-11-05",
        "serves": (
            "Qualifying low-income and needy households, and households making the transition "
            "from welfare to self-sufficiency. Federally funded through USDA and administered "
            "in Hawaii by DHS BESSD."
        ),
    },
    "hheap": {
        "name": "Hawaii Home Energy Assistance Program (H-HEAP)",
        "url": "https://humanservices.hawaii.gov/bessd/liheap/",
        "checked": "2026-11-05",
        "serves": (
            "Eligible Hawaii households. Provides a one-time payment toward an electric or gas "
            "bill for heating or cooling. Applications are processed by the Community Action "
            "Agency that serves the household's island. Households may receive only one type of "
            "H-HEAP payment per program year (October 1–September 30)."
        ),
    },
    "eoel": {
        "name": "Executive Office on Early Learning (EOEL)",
        "url": "https://earlylearning.hawaii.gov/",
        "checked": "2026-11-05",
        "serves": (
            "The state agency for early childhood education from birth to age five. "
            "Offers a free early learning program for 3- and 4-year-olds."
        ),
    },
    "kupuna_rent": {
        "name": "HPHA Rent Supplement Program for Kūpuna",
        "url": "https://hpha.hawaii.gov/rsp-interest-list",
        "checked": "2026-11-05",
        "serves": (
            "For seniors age 62 and older experiencing homelessness or at imminent risk of homelessness. "
            "Provides up to $500 per month toward rent, paid to the landlord. "
            "Joining the interest list does not guarantee assistance."
        ),
    },
}

# Med-QUEST official page was reachable on 2026-11-05 but did not yield a
# verifiable description of who it serves. It is listed as a limitation, not a program entry.
UNVERIFIED = {
    "medquest": {
        "name": "Med-QUEST",
        "url": "https://medquest.hawaii.gov/",
        "checked": "2026-11-05",
        "note": (
            "The official Med-QUEST page was reachable on 2026-11-05 but did not yield a "
            "verifiable description of who the program serves. No summary is provided."
        ),
    },
}

# field -> metadata. Ranking uses percent, not a composite.
MEASURES = {
    "householders_65plus_living_alone": {
        "label": "Households with a person age 65+ living alone",
        "denominator": "Total households",
        "table": "DP02",
        "pct_col": "householders_65plus_living_alone_percent",
        "pct_moe_col": "householders_65plus_living_alone_percent_moe",
        "est_col": "householders_65plus_living_alone_estimate",
        "est_moe_col": "householders_65plus_living_alone_moe",
        "raw_col": "householders_65plus_living_alone_raw_pct",
        "programs": ["snap", "hheap", "kupuna_rent"],
        "unverified": [],
    },
    "pct_people_poverty": {
        "label": "People below the poverty line",
        "denominator": "People for whom poverty status is determined",
        "table": "DP03",
        "pct_col": "pct_people_poverty_percent",
        "pct_moe_col": "pct_people_poverty_percent_moe",
        "est_col": "pct_people_poverty_estimate",
        "est_moe_col": "pct_people_poverty_moe",
        "programs": ["snap", "hheap"],
        "unverified": ["medquest"],
    },
    "pct_65plus_poverty": {
        "label": "People age 65+ below poverty",
        "denominator": "People age 65 and over for whom poverty status is determined",
        "table": "DP03",
        "pct_col": "pct_65plus_poverty_percent",
        "pct_moe_col": "pct_65plus_poverty_percent_moe",
        "est_col": "pct_65plus_poverty_estimate",
        "est_moe_col": "pct_65plus_poverty_moe",
        "programs": ["snap", "hheap", "kupuna_rent"],
        "unverified": [],
    },
    "pct_children_under5_poverty": {
        "label": "Related children under 5 in poverty",
        "denominator": "Related children of the householder under 5 years",
        "table": "DP03",
        "pct_col": "pct_children_under5_poverty_percent",
        "pct_moe_col": "pct_children_under5_poverty_percent_moe",
        "est_col": "pct_children_under5_poverty_estimate",
        "est_moe_col": "pct_children_under5_poverty_moe",
        "programs": ["eoel", "snap"],
        "unverified": ["medquest"],
    },
    "with_disability": {
        "label": "Population with a disability",
        "denominator": "Civilian noninstitutionalized population",
        "table": "DP02",
        "pct_col": "with_disability_percent",
        "pct_moe_col": "with_disability_percent_moe",
        "est_col": "with_disability_estimate",
        "est_moe_col": "with_disability_moe",
        "programs": ["snap"],
        "unverified": ["medquest"],
    },
    "limited_english": {
        "label": "Speak English less than “very well”",
        "denominator": "Population age 5 and over",
        "table": "DP02",
        "pct_col": "limited_english_percent",
        "pct_moe_col": "limited_english_percent_moe",
        "est_col": "limited_english_estimate",
        "est_moe_col": "limited_english_moe",
        "programs": [],
        "unverified": [],
    },
    "pct_no_health_insurance": {
        "label": "People without health insurance",
        "denominator": "Civilian noninstitutionalized population",
        "table": "DP03",
        "pct_col": "pct_no_health_insurance_percent",
        "pct_moe_col": "pct_no_health_insurance_percent_moe",
        "est_col": "pct_no_health_insurance_estimate",
        "est_moe_col": "pct_no_health_insurance_moe",
        "programs": [],
        "unverified": ["medquest"],
    },
    "no_vehicle": {
        "label": "Households with no vehicle available",
        "denominator": "Occupied housing units",
        "table": "DP04",
        "pct_col": "no_vehicle_percent",
        "pct_moe_col": "no_vehicle_percent_moe",
        "est_col": "no_vehicle_estimate",
        "est_moe_col": "no_vehicle_moe",
        "programs": [],
        "unverified": [],
    },
    "snap_benefits": {
        "label": "Households reporting SNAP (ACS survey, not DHS enrollment)",
        "denominator": "Households",
        "table": "DP03",
        "pct_col": "snap_benefits_percent",
        "pct_moe_col": "snap_benefits_percent_moe",
        "est_col": "snap_benefits_estimate",
        "est_moe_col": "snap_benefits_moe",
        "programs": ["snap"],
        "unverified": [],
    },
    "in_labor_force": {
        "label": "Labor force participation",
        "denominator": "Population 16 and over",
        "table": "DP03",
        "pct_col": "in_labor_force_percent",
        "pct_moe_col": "in_labor_force_percent_moe",
        "est_col": "in_labor_force_estimate",
        "est_moe_col": "in_labor_force_moe",
        "programs": [],
        "unverified": [],
    },
    "employed": {
        "label": "Employment rate",
        "denominator": "Population 16 and over",
        "table": "DP03",
        "pct_col": "employed_percent",
        "pct_moe_col": "employed_percent_moe",
        "est_col": "employed_estimate",
        "est_moe_col": "employed_moe",
        "programs": [],
        "unverified": [],
    },
    "rent_burden": {
        "label": "Renters spending 30%+ of income on rent",
        "denominator": "Renter households for whom GRAPI is computed",
        "table": "DP04",
        "computed": True,
        "programs": ["kupuna_rent"],
        "unverified": [],
    },
}


def _num(val):
    if val is None:
        return None
    s = str(val).replace(",", "").replace("%", "").replace("±", "").replace("$", "").strip()
    if s in ("", "(X)", "None", "nan", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def uncertainty_flag(percent, percent_moe):
    """Flag when the percent MOE exceeds 30% of the percent estimate.

    Missing values are not treated as zero. A zero estimate is flagged as
    a case where the MOE ratio is not defined.
    """
    if percent is None:
        return "missing"
    if percent == 0:
        return "zero estimate; MOE ratio not defined"
    if percent_moe is None:
        return "MOE not available"
    if percent_moe > 0.30 * percent:
        return "MOE exceeds 30% of estimate"
    return ""


def _load_rows(chamber: str):
    table = "house_districts" if chamber.lower() == "house" else "senate_districts"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY district").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _rent_burden(row):
    p1 = _num(row.get("rent_30_to_34_9_percent"))
    p2 = _num(row.get("rent_35_plus_percent"))
    m1 = _num(row.get("rent_30_to_34_9_percent_moe"))
    m2 = _num(row.get("rent_35_plus_percent_moe"))
    if p1 is None or p2 is None:
        return None, None, None, None
    pct = p1 + p2
    moe = math.sqrt((m1 or 0) ** 2 + (m2 or 0) ** 2) if (m1 is not None and m2 is not None) else None
    e1 = _num(row.get("rent_30_to_34_9_estimate"))
    e2 = _num(row.get("rent_35_plus_estimate"))
    em1 = _num(row.get("rent_30_to_34_9_moe"))
    em2 = _num(row.get("rent_35_plus_moe"))
    est = (e1 + e2) if (e1 is not None and e2 is not None) else None
    est_moe = math.sqrt((em1 or 0) ** 2 + (em2 or 0) ** 2) if (em1 is not None and em2 is not None) else None
    return pct, moe, est, est_moe


def rank_districts(chamber: str, measure_key: str):
    """Rank one chamber by one measure. Returns ranked rows and a missing count.

    Missing percent values are excluded and never converted to zero.
    """
    if chamber.lower() not in ("house", "senate"):
        raise ValueError("chamber must be house or senate")
    meta = MEASURES[measure_key]
    rows = _load_rows(chamber)
    ranked = []
    missing = 0
    for row in rows:
        if meta.get("computed"):
            pct, pct_moe, est, est_moe = _rent_burden(row)
        else:
            raw = row.get(meta.get("raw_col")) if meta.get("raw_col") else None
            pct = _num(raw) if raw is not None else _num(row.get(meta["pct_col"]))
            pct_moe = _num(row.get(meta["pct_moe_col"]))
            est = _num(row.get(meta["est_col"]))
            est_moe = _num(row.get(meta["est_moe_col"]))
        if pct is None:
            missing += 1
            continue
        ranked.append({
            "chamber": chamber.lower(),
            "district": row["district"],
            "measure": meta["label"],
            "percent": pct,
            "percent_display": f"{pct:.1f}%",
            "percent_moe": pct_moe,
            "percent_moe_display": f"±{pct_moe:.1f}" if pct_moe is not None else "",
            "estimate": est,
            "estimate_moe": est_moe,
            "denominator": meta["denominator"],
            "source_table": meta["table"],
            "year": YEAR,
            "uncertainty_flag": uncertainty_flag(pct, pct_moe),
            "sort_value": pct,
        })
    ranked.sort(key=lambda r: (-r["sort_value"], r["district"]))
    return ranked, missing


def comparison_csv(ranked):
    """CSV with source and uncertainty fields."""
    buf = io.StringIO()
    fields = [
        "chamber", "district", "measure", "percent", "percent_moe",
        "estimate", "estimate_moe", "denominator", "source_table", "year",
        "uncertainty_flag",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in ranked:
        writer.writerow(row)
    return buf.getvalue()


def programs_for(measure_key: str):
    meta = MEASURES[measure_key]
    return [PROGRAMS[k] for k in meta.get("programs", [])], [UNVERIFIED[k] for k in meta.get("unverified", [])]
