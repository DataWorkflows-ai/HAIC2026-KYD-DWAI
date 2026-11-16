"""Island, county and statewide program figures for a district's cards.

These figures are not published by legislative district, so they are shown as context for the island or
county the district sits in. Values come straight from Crystal's analyses in scripts/ (Med-QUEST
enrollment, TANF by island, county SNAP from the BESSD workbook) and her district-level TANF
under-enrollment comparison. No numbers are re-derived here.
"""
from __future__ import annotations
import json
import sys
from functools import lru_cache

from ..config import settings
from .cache import cached

COUNTY_ISLANDS = {  # county (district_counties.json) → Med-QUEST island keys, TANF island, county-SNAP keys
    "Oahu": (["oahu"], "OAHU", ["Honolulu"]),
    "Hawaii": (["hawaii"], "HAWAII", ["Hawaii"]),
    "Maui": (["maui", "molokai", "lanai"], "MAUI", ["Maui", "Molokai", "Lanai"]),
    "Kauai": (["kauai"], "KAUAI", ["Kauai"]),
}
ISLAND_LABEL = {"oahu": "Oʻahu", "hawaii": "Hawaiʻi Island", "maui": "Maui", "kauai": "Kauaʻi",
                "molokai": "Molokaʻi", "lanai": "Lānaʻi", "Honolulu": "Oʻahu", "Hawaii": "Hawaiʻi County",
                "Maui": "Maui Island", "Kauai": "Kauaʻi", "Molokai": "Molokaʻi", "Lanai": "Lānaʻi"}


@lru_cache(maxsize=1)
def _scripts():
    path = str(settings().data_dir.parents[1] / "scripts")
    if path not in sys.path:
        sys.path.insert(0, path)
    import load_county_snap, medquest, tanf_by_island, tanf_underenrollment  # noqa: E401
    return load_county_snap, medquest, tanf_by_island, tanf_underenrollment


@lru_cache(maxsize=1)
def _static() -> dict:
    """Island/county figures are the same for every district; compute once per process."""
    county_snap, mq, tanf_isl, _ = _scripts()
    month, snap_rows = county_snap.county_snap()
    return {"medquest": mq.get_medquest(), "medquest_ratio": mq.get_medquest_island_ratio(),
            "medquest_trend": mq.get_medquest_trend("statewide"), "tanf_island": tanf_isl.get_tanf_by_island(month),
            "county_snap": {"month": month, "rows": {c: {"households": h, "persons": p} for c, h, p, _ in snap_rows}}}


@lru_cache(maxsize=1)
def _facts() -> list[dict]:
    """Statewide program facts (income limits, latest enrollment, source link) from the research package."""
    import csv
    p = settings().data_dir / "program_facts.csv"
    return list(csv.DictReader(p.open(encoding="utf-8"))) if p.exists() else []


@cached
def context(geo_id: str) -> dict:
    counties = json.loads((settings().data_dir / "district_counties.json").read_text())
    county = counties.get(geo_id)
    if not county:
        raise KeyError(geo_id)
    mq_keys, tanf_key, snap_keys = COUNTY_ISLANDS[county]
    s = _static()
    _, _, _, under = _scripts()
    chamber = "house" if geo_id.startswith("HD") else "senate"

    mq = s["medquest"]
    ratio = {x["island"]: x for x in s["medquest_ratio"]["islands"]}
    tanf = next((x for x in s["tanf_island"]["islands"] if x["island"] == tanf_key), None)
    ue = under.get_tanf_underenrollment(chamber, int(geo_id[3:]))
    from .repo import repo
    hud_keys = ["hud_units_total", "hud_units_hcv", "hud_units_public_housing", "hud_units_pbs8",
                "hud_units_elderly_disabled", "hud_people_total", "hud_units_per_1k_hh"]
    hud = {o.indicator: o for o in repo().observations([geo_id], hud_keys)}
    hud_state = {o.indicator: o for o in repo().observations(["HI"], ["hud_units_per_1k_hh"])}
    meals = {o.indicator: o for o in repo().observations([geo_id],
             ["pct_free_reduced_meals", "free_reduced_students", "public_school_enrolled"])}
    meals_state = {o.indicator: o.value for o in repo().observations(["HI"], ["pct_free_reduced_meals"])}
    return {
        "geo_id": geo_id, "county": county,
        "school_meals": {"title": "Free/reduced-price school meals (SY2025-26)",
                         "observations": list(meals.values()), "state_pct": meals_state.get("pct_free_reduced_meals"),
                         "source": "Hawaiʻi Child Nutrition Programs, October Data SY2025-26",
                         "url": "https://hcnp.hawaii.gov/wp-content/uploads/2026/01/October-Data-2026-SY25-26.pdf",
                         "note": "* Excludes public charter schools, which enroll students statewide regardless of "
                                 "district. Counted by school location, not where students live."},
        "facts": _facts(),
        "hud": {"title": "HUD-subsidized housing (district)", "as_of": "2025-12-31",
                "observations": [hud[k] for k in hud_keys if k in hud],
                "state_per_1k_hh": hud_state["hud_units_per_1k_hh"].value if hud_state else None,
                "source": "HUD Picture of Subsidized Households 2025, census tracts allocated to districts by 2020 population",
                "caveats": ["Suppressed small cells count as 0, so district figures are a floor.",
                            "About 2,400 statewide units HUD could not place in a tract are excluded from districts."]},
        "medquest": {
            "title": "Med-QUEST enrollment (island)", "sfy": mq["sfy"], "statewide": mq["statewide"],
            "islands": [{"island": ISLAND_LABEL[k], **mq["islands"][k],
                         "enrollment_to_need_ratio": ratio.get(k, {}).get("enrollment_to_need_ratio")} for k in mq_keys],
            "trend": s["medquest_trend"]["series"], "source": mq["source"], "caveats": mq["caveats"]},
        "tanf_island": {
            "title": "TANF caseload (island/county)", "month": s["tanf_island"]["month"], **(tanf or {}),
            "source": s["tanf_island"]["source_caseload"], "note": s["tanf_island"]["note"]},
        "county_snap": {
            "title": "SNAP participation (island/county)", "month": s["county_snap"]["month"],
            "rows": [{"area": ISLAND_LABEL[k], **s["county_snap"]["rows"][k]} for k in snap_keys if k in s["county_snap"]["rows"]],
            "source": "Hawaiʻi DHS BESSD SFY 2026 monthly summary (SNAP households and persons, all categories)"},
        "tanf_underenrollment": {
            "title": "TANF reach by race (district poverty vs statewide TANF)",
            "available": ue.get("data_available", False),
            "poverty_population": ue.get("poverty_population"),
            "groups": [{k: g[k] for k in ("label", "poverty_count", "district_poverty_share_percent",
                                          "statewide_tanf_share_percent", "under_enrollment_pp", "note")}
                       for g in ue.get("groups", [])],
            "caveats": ue.get("caveats", [])},
    }
