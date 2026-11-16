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
    score_keys = ["pct_sba_ela_proficient", "pct_sba_math_proficient", "pct_hsa_science_proficient", "sba_tested"]
    tests = {o.indicator: o for o in repo().observations([geo_id], score_keys)}
    tests_state = {o.indicator: o.value for o in repo().observations(["HI"], score_keys)}
    cfips = {"Oahu": "15003", "Hawaii": "15001", "Maui": "15009", "Kauai": "15007"}[county]
    emp_keys = ["laus_unemp_rate", "laus_labor_force", "laus_unemployed", "unemployment_rate"]
    emp = {o.indicator: o for o in repo().observations([geo_id], emp_keys)}
    cty = {o.indicator: o for o in repo().observations([f"CNTY-{cfips}"], emp_keys)}
    sta = {o.indicator: o for o in repo().observations(["HI"], emp_keys)}
    years = range(2014, 2026)
    trend_keys = [f"laus_unemp_rate_{y}" for y in years if y != 2025] + ["laus_unemp_rate"]
    tr = {(o.geo_id, o.indicator): o.value for o in repo().observations([f"CNTY-{cfips}", "HI"], trend_keys)}
    def ty(y):
        return "laus_unemp_rate" if y == 2025 else f"laus_unemp_rate_{y}"
    crime = None
    if county == "Oahu":
        ck = ["crime_total_est", "crime_violent_est", "crime_property_est", "crime_rate_per_1k_est", "crime_violent_per_1k_est"]
        dist = {o.indicator: o for o in repo().observations([geo_id], ck)}
        cyears = range(2017, 2026)
        tkeys = [f"crime_total_est_{y}" for y in cyears if y != 2025] + ["crime_total_est"]
        tv = {(o.geo_id, o.indicator): o.value for o in repo().observations([geo_id, "CNTY-15003"], tkeys)}
        tk = lambda y: "crime_total_est" if y == 2025 else f"crime_total_est_{y}"
        ohu = [o.value for o in repo().observations([g for g, c in counties.items() if c == "Oahu" and g[:2] == geo_id[:2]],
                                                    ["crime_rate_per_1k_est"]) if o.value is not None]
        crime = {"title": "Crime (Oʻahu) — ESTIMATE", "year": 2025,
                 "district": [dist[k] for k in ck if k in dist],
                 "honolulu_official": [o for o in repo().observations(["CNTY-15003"], ["crime_total_est", "crime_violent_est",
                                                                                         "crime_property_est"])],
                 "oahu_median_per_1k": sorted(ohu)[len(ohu) // 2] if ohu else None,
                 "trend": [{"year": y, "district": tv.get((geo_id, tk(y))), "honolulu_official": tv.get(("CNTY-15003", tk(y)))}
                           for y in cyears],
                 "credit": "HPD Annual Reports; beat geometry traced from HPD 2025 report maps (map data Google)",
                 "caveats": ["ESTIMATE / APPROXIMATE: HPD publishes no beat map files, so beat boundaries were traced from "
                             "the 2025 report maps (about 50–150 m error in town) and offenses were split to districts by "
                             "2020 population.",
                             "Beat counts are raw case counts and run about 7–17% above HPD's official Table 1 totals "
                             "(shown for the City & County).",
                             "Per-resident rates overstate crime where visitors and workers outnumber residents "
                             "(Waikīkī, Ala Moana, downtown, airport).",
                             "Not comparable with the Attorney General's NIBRS dashboard."]}
    return {
        "geo_id": geo_id, "county": county, "crime": crime,
        "employment": {
            "title": "Unemployment", "district": [emp[k] for k in emp_keys if k in emp],
            "county": [cty[k] for k in ("laus_unemp_rate", "laus_labor_force") if k in cty],
            "state": [sta[k] for k in ("laus_unemp_rate", "laus_labor_force") if k in sta],
            "trend": [{"year": y, "county": tr.get((f"CNTY-{cfips}", ty(y))), "state": tr.get(("HI", ty(y)))} for y in years],
            "source": "DBEDT/DLIR LAUS annual averages (tract and county); ACS 2020–2024 for comparison",
            "notes": ["2025 district rates are DBEDT tract estimates (current county totals split by ACS 2020–2024 shares) "
                      "allocated to districts by population; the county figures are official LAUS totals.",
                      "The ACS 2020–2024 rate is a five-year survey average that includes the 2020–21 pandemic "
                      "years and uses a different definition, so it runs higher than the 2025 LAUS rate."]},
        "school_meals": {"title": "Free/reduced-price school meals (SY2025-26)",
                         "observations": list(meals.values()), "state_pct": meals_state.get("pct_free_reduced_meals"),
                         "source": "Hawaiʻi Child Nutrition Programs, October Data SY2025-26",
                         "url": "https://hcnp.hawaii.gov/wp-content/uploads/2026/01/October-Data-2026-SY25-26.pdf",
                         "note": "* Excludes public charter schools, which enroll students statewide regardless of "
                                 "district. Counted by school location, not where students live."},
        "test_scores": {"title": "Test scores (2025 Smarter Balanced and HSA Science)",
                        "observations": [tests[k] for k in score_keys if k in tests],
                        "state": {k: tests_state.get(k) for k in score_keys[:3]},
                        "source": "Hawaiʻi State Department of Education, 2025 results by school",
                        "url": "https://hawaiipublicschools.org/academics/types-of-testing/",
                        "note": "* Public schools located in the district; excludes public charter schools, which "
                                "enroll statewide. Counted by school location, not where students live. Results "
                                "HIDOE suppresses for student privacy are left out."},
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
