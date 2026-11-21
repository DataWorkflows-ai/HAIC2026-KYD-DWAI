"""Demo-ready program gap summaries and school-level drilldowns.

All values are aggregate public data. Rows that are not published for a district are labelled as
state anchors or allocated estimates; nothing here is an individual eligibility determination.
"""
from __future__ import annotations

from . import datastore
from .repo import repo

PROGRAM_LINKS = {
    "snap": "https://humanservices.hawaii.gov/bessd/snap/",
    "wic": "https://health.hawaii.gov/wic/",
    "medquest": "https://medquest.hawaii.gov/",
    "tanf": "https://humanservices.hawaii.gov/bessd/",
    "school_meals": "https://hcnp.hawaii.gov/",
    "act139": "https://hawaiipublicschools.org/2026-expanded-free-school-meals/",
    "hheap": "https://humanservices.hawaii.gov/bessd/energy-assistance-programs/",
    "lifeline": "https://www.lifelinesupport.org/",
}


def _obs(geo_id: str, keys: list[str]) -> dict:
    return {o.indicator: o for o in repo().observations([geo_id], keys)}


def _row(program_id: str, name: str, unit: str, geography: str, source: str, *,
         eligible=None, enrolled=None, gap=None, reach=None, range_low=None, range_high=None,
         basis: str, caveats: list[str] | None = None, unavailable: str | None = None) -> dict:
    return {
        "program_id": program_id,
        "name": name,
        "unit": unit,
        "geography": geography,
        "source": source,
        "official_url": PROGRAM_LINKS[program_id],
        "eligible": eligible,
        "enrolled": enrolled,
        "gap": gap,
        "reach": reach,
        "range_low": range_low,
        "range_high": range_high,
        "basis": basis,
        "caveats": caveats or [],
        "unavailable": unavailable,
    }


def _derived_count(geo_id: str, indicator: str, label: str, value: float | None, note: str, source_id: str) -> dict | None:
    if value is None:
        return None
    return {"obs_id": f"derived-{geo_id}-{indicator}", "geo_id": geo_id, "indicator": indicator, "label": label,
            "unit": "count", "value": float(value), "moe": None, "cv": None, "vintage": "2020-2024",
            "method": "derived", "method_note": note, "source_id": source_id, "flags": ["estimate"]}


def _school_rows(geo_id: str) -> list[dict]:
    cep = {r["school_id"]: r for r in datastore.csv_rows("cep_schools_sy2026_27.csv")}
    rows = []
    for r in datastore.csv_rows("school_meals_by_school.csv"):
        if geo_id.startswith("HD") and int(float(r["house_2022"])) != int(geo_id[3:]):
            continue
        if geo_id.startswith("SD") and int(float(r["senate_2022"])) != int(geo_id[3:]):
            continue
        c = cep.get(str(r["site_id"]))
        rows.append({
            "school_name": r["school_name"],
            "house": f"HD-{int(float(r['house_2022'])):02d}",
            "senate": f"SD-{int(float(r['senate_2022'])):02d}",
            "complex_area": r.get("complex_area") or "",
            "island_or_district": r.get("hidoe_district") or "",
            "enrollment": float(r["enrolled"]),
            "free_reduced": float(r["fr"]),
            "cep_status": c["cep_status"] if c else "not_listed",
            "source_year": "HCNP October SY2025-26 eligibility report; CEP SY2026-27 workbook when listed",
            "source_url": r["source_url"],
        })
    return rows


def _cep_rows(geo_id: str, statuses: set[str] | None = None) -> list[dict]:
    out = []
    for r in datastore.csv_rows("cep_schools_sy2026_27.csv"):
        if statuses and r["cep_status"] not in statuses:
            continue
        if geo_id.startswith("HD"):
            if not r["house_2022"] or int(float(r["house_2022"])) != int(geo_id[3:]):
                continue
        if geo_id.startswith("SD"):
            if not r["senate_2022"] or int(float(r["senate_2022"])) != int(geo_id[3:]):
                continue
        out.append({
            "school_name": r["school_name"],
            "house": f"HD-{int(float(r['house_2022'])):02d}" if r["house_2022"] else "",
            "senate": f"SD-{int(float(r['senate_2022'])):02d}" if r["senate_2022"] else "",
            "complex_area": r["complex_area"],
            "island_or_district": r["hidoe_district"],
            "enrollment": float(r["oct_enrolled"] or 0),
            "free_reduced": float(r["oct_free_reduced"] or 0),
            "cep_status": r["cep_status"],
            "source_year": r["source_year"],
            "source_url": r["source_url"],
        })
    return out


def _attach_snap_receipt(row: dict, obs: dict) -> None:
    """Households and people who report SNAP. These exist for House and Senate districts even when the
    poverty-household gap has not been loaded."""
    row["receiving_households"] = obs.get("snap_hh_count")
    row["receiving_persons"] = obs.get("snap_persons_est")
    row["receiving_pct"] = obs.get("pct_snap_hh")


def _totals(rows: list[dict]) -> dict:
    return {
        "schools": len(rows),
        "enrollment": round(sum(r["enrollment"] for r in rows)),
        "free_reduced": round(sum(r["free_reduced"] for r in rows)),
        "uncertified": round(sum(r["enrollment"] - r["free_reduced"] for r in rows)),
    }


def program_gaps(geo_id: str) -> dict:
    if not repo().geography(geo_id):
        raise KeyError(geo_id)
    district = _obs(geo_id, [
        "snap_poverty_hh_total", "snap_poverty_hh_receiving", "snap_strict_gap_households",
        "snap_poverty_hh_reach_rate", "snap_eligible_usda", "snap_participants_usda",
        "snap_gap_low_persons", "snap_gap_usda_low", "snap_gap_usda_high", "snap_participation_rate",
        "wic_eligible_est", "wic_participating_est", "wic_gap_est", "wic_reach_est",
        "medquest_uninsured_eligible", "medquest_covered_acs", "medquest_reach_proxy",
        "tanf_deep_poverty_children", "tanf_reach_low", "tanf_reach_high",
        "free_reduced_students", "public_school_enrolled", "pct_free_reduced_meals",
        "act139_acs_upper_children", "act139_hidoe_expected_children",
        "snap_hh_count", "snap_persons_est", "pct_snap_hh",
    ])
    state = _obs("HI", list(district.keys()) + [
        "snap_eligible_usda", "snap_participants_usda", "snap_gap_low_persons",
        "snap_gap_usda_low", "snap_gap_usda_high", "snap_participation_rate", "tanf_reach_low", "tanf_reach_high",
        "act139_hidoe_expected_children",
    ])
    schools = _school_rows(geo_id)
    cep_not = _cep_rows(geo_id, {"eligible_not_participating"})
    cep_part = _cep_rows(geo_id, {"participating"})

    if geo_id == "HI":
        snap = _row("snap", "SNAP", "people", "Statewide, federal-rules eligibility",
                    "USDA FY2022 SNAP participation report",
                    eligible=state.get("snap_eligible_usda"), enrolled=state.get("snap_participants_usda"),
                    gap=state.get("snap_gap_low_persons"), range_low=state.get("snap_gap_usda_low"),
                    range_high=state.get("snap_gap_usda_high"), reach=state.get("snap_participation_rate"),
                    basis="Official state anchor", caveats=["About 31,000 eligible people not participating; USDA range about 15,000-46,000."])
    else:
        snap = _row("snap", "SNAP", "poverty households", "District, ACS 2020-2024",
                    "ACS B22003 by 2022 legislative district",
                    eligible=district.get("snap_poverty_hh_total"), enrolled=district.get("snap_poverty_hh_receiving"),
                    gap=district.get("snap_strict_gap_households"), reach=district.get("snap_poverty_hh_reach_rate"),
                    basis="District-native survey estimate", caveats=["Use this for district rankings; USDA's 30,916 is statewide only."])
    _attach_snap_receipt(snap, district)
    med_covered = district.get("medquest_covered_acs")
    med_gap = district.get("medquest_uninsured_eligible")
    med_eligible = _derived_count(geo_id, "medquest_eligible_proxy", "People covered by Medicaid/means-tested coverage plus uninsured eligible",
                                  (med_covered.value if med_covered else 0) + (med_gap.value if med_gap else 0)
                                  if (med_covered and med_gap) else None,
                                  "C27007 covered plus C27016 uninsured-eligible; mixed-universe proxy for display only.",
                                  "acs5_2024_c27016_sld")
    if geo_id == "HI":
        act139_low, act139_high = state.get("act139_hidoe_expected_children"), district.get("act139_acs_upper_children")
        act139_geo = "Statewide HIDOE projection / ACS upper bound"
    else:
        act139_low, act139_high = None, district.get("act139_acs_upper_children")
        act139_geo = "District ACS upper bound"

    rows = [
        snap,
        _row("wic", "WIC", "people", "District allocation of state anchor" if geo_id != "HI" else "Statewide",
             "FNS WIC EER CY2023 and FNS Aug 2026 monthly participation",
             eligible=district.get("wic_eligible_est"), enrolled=district.get("wic_participating_est"),
             gap=district.get("wic_gap_est"), reach=district.get("wic_reach_est"),
             basis="Allocated estimate" if geo_id != "HI" else "State anchor",
             caveats=["No public district or clinic caseload; district rate equals the state rate by construction."]),
        _row("medquest", "Med-QUEST / CHIP", "people", "District, ACS 2020-2024",
             "ACS C27016/C27007 by 2022 legislative district",
             eligible=med_eligible, enrolled=district.get("medquest_covered_acs"),
             gap=district.get("medquest_uninsured_eligible"), reach=district.get("medquest_reach_proxy"),
             basis="District-native uninsured gap", caveats=["Reach proxy mixes covered all ages with uninsured under-65; use the gap count as the solid figure."]),
        _row("tanf", "TANF / TAONF", "children", "State reach; district need proxy",
             "ACS B17024, ACF FY2025 TANF workbook, DHS Databook SFY2025",
             eligible=district.get("tanf_deep_poverty_children"), range_low=state.get("tanf_reach_low"),
             range_high=state.get("tanf_reach_high"), basis="Proxy range",
             caveats=["No official eligible count; reach is 18.7-24.0% statewide against children below 50% FPL."]),
        _row("school_meals", "School meals eligibility", "students", "Schools located in geography",
             "HCNP October SY2025-26 eligibility report",
             eligible=district.get("public_school_enrolled"), enrolled=district.get("free_reduced_students"),
             gap=None, reach=district.get("pct_free_reduced_meals"), basis="Eligibility, not meals served",
             caveats=["Public non-charter schools only in district rollup; charters enroll statewide."]),
        _row("act139", "Act 139 free-meal expansion", "children", act139_geo,
             "ACS B17024 and HIDOE July 2026 release",
             range_low=act139_low, range_high=act139_high,
             basis="Range, not a point gap" if geo_id == "HI" else "ACS upper-bound estimate",
             caveats=["Statewide: HIDOE expects about 12,000 additional students; ACS upper bound is about 36,500 children."
                      if geo_id == "HI" else "District value is the ACS upper-bound count only; the 12,000 HIDOE projection is statewide and is not shown as a district low end."]),
        _row("hheap", "H-HEAP utilities", "households", "Statewide only",
             "DHS/ACF public program facts", basis="Data unavailable by district",
             unavailable="No public district enrollment or eligible count in the current data package.",
             caveats=["Use SNAP/SSI household counts only as outreach leads, not eligibility determinations."]),
        _row("lifeline", "Lifeline utilities", "households", "Program rule only",
             "FCC/USAC Lifeline rules", basis="Data unavailable by district",
             unavailable="No public district enrollment count in the current data package.",
             caveats=["SNAP, Medicaid, SSI, housing and income routes overlap; no local uptake gap is computed."]),
    ]

    return {
        "geo_id": geo_id,
        "disclaimer": "Informational only. Program agencies decide eligibility. Counts describe populations, not individuals.",
        "rows": rows,
        "state_rows": {k: v for k, v in state.items()},
        "school_meals": {"rows": schools, "totals": _totals(schools)},
        "cep": {
            "eligible_not_participating": {"rows": cep_not, "totals": _totals(cep_not)},
            "participating": {"rows": cep_part, "totals": _totals(cep_part)},
        },
        "map_indicators": ["snap_strict_gap_households", "medquest_uninsured_eligible", "wic_gap_est", "act139_acs_upper_children"],
    }
