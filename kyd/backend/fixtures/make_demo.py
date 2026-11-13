"""Generate SYNTHETIC demo fixtures so the UI and agent can be built before ETL lands.

These values are random and are NOT real ACS figures. Every observation is
flagged 'demo', and the UI shows a DEMO banner while fixture mode is on.
Run: python backend/fixtures/make_demo.py
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).parent
rnd = random.Random(2026)

COUNTIES = {"CNTY-15001": "Hawaiʻi County", "CNTY-15003": "City & County of Honolulu",
            "CNTY-15007": "Kauaʻi County", "CNTY-15009": "Maui County"}

def county_for(kind: str, n: int) -> str:   # approximate, demo only
    if kind == "SD":
        return "CNTY-15001" if n <= 4 else "CNTY-15009" if n <= 7 else "CNTY-15007" if n == 8 else "CNTY-15003"
    return "CNTY-15001" if n <= 7 else "CNTY-15009" if n <= 14 else "CNTY-15007" if n <= 17 else "CNTY-15003"

geos = [{"geo_id": "HI", "geo_type": "state", "name": "State of Hawaiʻi", "counties": list(COUNTIES)}]
geos += [{"geo_id": k, "geo_type": "county", "name": v, "counties": [k]} for k, v in COUNTIES.items()]
geos += [{"geo_id": f"SD-{i:02d}", "geo_type": "sldu", "name": f"Senate District {i}",
          "counties": [county_for("SD", i)]} for i in range(1, 26)]
geos += [{"geo_id": f"HD-{i:02d}", "geo_type": "sldl", "name": f"House District {i}",
          "counties": [county_for("HD", i)]} for i in range(1, 52)]

# indicator, label, unit, topic, ACS table/var, (lo, hi), relative MOE
INDICATORS = [
    ("total_pop", "Total population", "count", "population", "B01003_001", (17000, 60000), 0.04),
    ("median_age", "Median age", "years", "age", "B01002_001", (32, 52), 0.05),
    ("pct_under18", "Under 18", "pct", "age", "S0101", (14, 27), 0.10),
    ("pct_65plus", "65 and over", "pct", "age", "S0101", (12, 32), 0.10),
    ("median_hh_income", "Median household income", "usd", "income", "B19013_001", (58000, 140000), 0.09),
    ("pct_below_fpl", "Below poverty level", "pct", "income", "S1701", (4, 20), 0.25),
    ("pct_below_200fpl", "Below 200% of poverty", "pct", "income", "C17002", (12, 42), 0.15),
    ("pct_snap_hh", "Households receiving SNAP", "pct", "assistance", "B22003", (3, 22), 0.30),
    ("pct_rent_burden_30", "Renters paying 30%+ of income", "pct", "housing", "B25070", (38, 68), 0.12),
    ("pct_uninsured", "Without health insurance", "pct", "health", "S2701", (1.5, 8), 0.40),
    ("pct_disability", "With a disability", "pct", "health", "S1810", (8, 17), 0.15),
    ("pct_veterans", "Civilian veterans (18+)", "pct", "population", "S2101", (4, 14), 0.18),
    ("pct_limited_english", "Limited English households", "pct", "language", "S1602", (1, 14), 0.30),
    ("unemployment_rate", "Unemployment rate", "pct", "employment", "S2301", (2, 8), 0.30),
]

obs, i = [], 0
for g in geos:
    for key, label, unit, topic, acs, (lo, hi), rmoe in INDICATORS:
        if g["geo_type"] in ("state", "county") and key == "total_pop":
            v = {"HI": 1440000, "CNTY-15003": 1005000, "CNTY-15001": 205000,
                 "CNTY-15009": 165000, "CNTY-15007": 73000}[g["geo_id"]]
        else:
            v = round(rnd.uniform(lo, hi), 1 if unit in ("pct", "years") else 0)
        if g["geo_type"] in ("state", "county"):
            rmoe_eff = rmoe / 4
        else:
            rmoe_eff = rmoe * rnd.uniform(0.6, 1.6)
        moe = round(v * rmoe_eff, 1)
        i += 1
        obs.append({"obs_id": f"demo-{i}", "geo_id": g["geo_id"], "indicator": key, "label": label,
                    "unit": unit, "topic": topic, "acs": acs, "value": v, "moe": moe,
                    "vintage": "2019-2023", "method": "direct", "source_id": "acs5_2023_demo"})

PROGRAMS = [
    ("snap", "SNAP (Food Stamps)", "DHS / BESSD", "federal", "Monthly food benefits for low-income households.",
     "https://humanservices.hawaii.gov/bessd/snap/", ["low_income_households"], ["pct_below_200fpl", "pct_snap_hh"]),
    ("wic", "WIC", "DOH", "federal", "Nutrition support for pregnant people, infants and children under 5.",
     "https://health.hawaii.gov/wic/", ["young_children", "low_income_households"], ["pct_under18", "pct_below_200fpl"]),
    ("med_quest", "Med-QUEST (Medicaid)", "DHS / MQD", "state", "Health coverage for eligible low-income residents.",
     "https://medquest.hawaii.gov/", ["uninsured", "low_income_households"], ["pct_uninsured", "pct_below_200fpl"]),
    ("liheap", "LIHEAP Energy Assistance", "DHS / BESSD", "federal", "Help with home energy bills.",
     "https://humanservices.hawaii.gov/bessd/liheap/", ["low_income_households"], ["pct_below_fpl"]),
    ("eitc", "Earned Income Tax Credit", "IRS / DOTAX", "federal", "Refundable tax credit for working families.",
     "https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit-eitc", ["working_families"], ["pct_below_200fpl"]),
    ("kupuna_care", "Kūpuna Care", "DOH / EOA", "state", "In-home and community services for older adults.",
     "https://health.hawaii.gov/eoa/", ["older_adults"], ["pct_65plus"]),
    ("ssi", "Supplemental Security Income", "SSA", "federal", "Monthly payments for aged, blind or disabled people with low income.",
     "https://www.ssa.gov/ssi", ["older_adults", "people_with_disabilities"], ["pct_disability", "pct_65plus"]),
    ("aca", "ACA Marketplace Subsidies", "CMS", "federal", "Premium tax credits for marketplace health plans.",
     "https://www.healthcare.gov/", ["uninsured"], ["pct_uninsured"]),
    ("hcv", "Housing Choice Vouchers (Section 8)", "HPHA / HUD", "federal", "Rental assistance for low-income renters.",
     "https://www.hud.gov/topics/housing_choice_voucher_program_section_8", ["rent_burdened"], ["pct_rent_burden_30"]),
    ("va_benefits", "VA Health & Benefits", "VA", "federal", "Health care and benefits for veterans.",
     "https://www.va.gov/", ["veterans"], ["pct_veterans"]),
    ("lep_services", "Language Access Services", "Office of Language Access", "state", "Interpretation and translation for state services.",
     "https://health.hawaii.gov/ola/", ["limited_english"], ["pct_limited_english"]),
    ("ui_workforce", "American Job Centers", "DLIR / WDD", "state", "Job search, training and unemployment help.",
     "https://labor.hawaii.gov/wdc/", ["job_seekers"], ["unemployment_rate"]),
]
programs = [dict(zip(["program_id", "name", "agency", "level", "summary", "official_url", "populations",
                      "proxy_indicators"], p)) | {"url_verified": False} for p in PROGRAMS]

sources = [{"source_id": "acs5_2023_demo", "publisher": "SYNTHETIC DEMO DATA",
            "title": "Placeholder modeled on ACS 5-year 2019–2023 (state legislative districts)",
            "url": "https://api.census.gov/data/2023/acs/acs5", "release_date": "2024-12-12"}]

for name, data in [("geographies", geos), ("observations", obs), ("programs", programs), ("sources", sources)]:
    (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(geos)} geos, {len(obs)} observations, {len(programs)} programs")
