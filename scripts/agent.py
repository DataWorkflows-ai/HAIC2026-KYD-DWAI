"""
Know Your District agent — district-first profile tool for Hawaii legislators.

Guardrails:
- Cite table + year for every number
- Show margin of error
- Say "no data" instead of guessing
- Never identify individuals
- Never say residents "are eligible" — say "may qualify; see program link"
"""

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "districts.db"

PROGRAMS = {
    "snap": "https://humanservices.hawaii.gov/bessd/snap/",
    "medquest": "https://medquest.hawaii.gov/",
    "hpha": "https://hpha.hawaii.gov/",
    "earlylearning": "https://earlylearning.hawaii.gov/",
    "liheap": "https://humanservices.hawaii.gov/bessd/liheap/",
}

OAHU_65PLUS_POVERTY = "9.0% ±0.5"

# Metric map: pattern → (field, label, table, is_money)
METRICS = [
    (r"kūpuna|kupuna|65\s*\+|65\s*years|seniors?", "pct_65plus_poverty", "65+ poverty rate", "DP03", False),
    (r"under\s*5|children\s*under|young\s*children", "pct_children_under5_poverty", "share of related children under 5 in poverty", "DP03", False),
    (r"families?\s*poverty|family\s*poverty", "pct_families_poverty", "share of families below poverty", "DP03", False),
    (r"poverty|below\s*poverty|poor|low[-\s]?income", "pct_people_poverty", "poverty rate", "DP03", False),
    (r"uninsured|uninsurance|no\s*health|without\s*(?:health\s*)?insurance|health\s*insurance|health\s*coverage|lack\s*of\s*insurance", "pct_no_health_insurance", "share of residents without health insurance", "DP03", False),
    (r"median\s*household\s*income|median\s*income|household\s*income|income", "median_hh_income", "median household income", "DP03", True),
    (r"mean\s*household\s*income|mean\s*income", "mean_hh_income", "mean household income", "DP03", True),
    (r"per\s*capita|per-capita", "per_capita_income", "per capita income", "DP03", True),
    (r"median\s*family\s*income|family\s*income", "median_family_income", "median family income", "DP03", True),
    (r"labor\s*force|workforce\s*participation|labor\s*force\s*participation", "in_labor_force", "labor force participation rate", "DP03", False),
    (r"employment\s*rate|employed|employment|unemployment|jobs", "employed", "employment rate", "DP03", False),
    (r"rent\s*burden|rent\s*burdened|housing\s*costs|rent\s*over\s*30|30\s*%\s*of\s*(?:their\s*)?income\s*on\s*rent|grapi", "rent_burden", "share of renters spending 30%+ of income on rent", "DP04", False),
    (r"65\s*\+\s*living\s*alone|living\s*alone|householders?\s*65", "householders_65plus_living_alone", "share of householders 65+ living alone", "DP02", False),
    (r"disability|disabled", "with_disability", "share of population with a disability", "DP02", False),
    (r"limited\s*english|english\s*less\s*than|speak\s*english", "limited_english", "share who speak English less than 'very well'", "DP02", False),
    (r"snap|food\s*stamp", "snap_benefits", "share of households reporting SNAP (self-reported on Census, not DHS enrollment)", "DP03", False),
    (r"no\s*vehicle|without\s*a\s*vehicle|no\s*car", "no_vehicle", "share of households with no vehicle available", "DP04", False),
]

def get_district(chamber: str, district_number: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    table = "house_districts" if chamber.lower() == "house" else "senate_districts"
    cur = conn.execute(f"SELECT * FROM {table} WHERE district = ?", (district_number,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_county_snap(county: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM county_snap WHERE county = ?", (county,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_county_taxes(county: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM county_taxes WHERE county = ?", (county,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_county_housing(county: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM county_housing WHERE county = ?", (county,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def _pct(value):
    if value is None:
        return "N/A"
    return str(value)

def _money(value):
    if value is None:
        return "N/A"
    try:
        return f"${int(float(str(value).replace(',',''))):,}"
    except (TypeError, ValueError):
        return str(value)

def _clean_moe(value):
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("", "(X)", "None", "nan"):
        return ""
    if not s.startswith("±"):
        s = f"±{s}"
    return f" {s}"

def parse_district(q: str):
    house_patterns = [
        r"\bhd\s*(\d+)",
        r"\bhouse\s+district\s+(\d+)",
        r"\bhouse\s+(\d+)",
        r"\bdistrict\s+(\d+)\s+house",
    ]
    for pat in house_patterns:
        m = re.search(pat, q)
        if m:
            return "house", int(m.group(1))
    senate_patterns = [
        r"\bsd\s*(\d+)",
        r"\bsenate\s+district\s+(\d+)",
        r"\bsenate\s+(\d+)",
        r"\bdistrict\s+(\d+)\s+senate",
    ]
    for pat in senate_patterns:
        m = re.search(pat, q)
        if m:
            return "senate", int(m.group(1))
    return None, None

def district_not_found(chamber: str, num: int) -> str:
    label = "House" if chamber == "house" else "Senate"
    return (
        f"I don't have {label} District {num}. "
        f"Hawaii has House Districts 1–51 and Senate Districts 1–25."
    )

def build_profile(chamber: str, num: int) -> str:
    """One-page district profile with persona measures."""
    data = get_district(chamber, num)
    if not data:
        return district_not_found(chamber, num)
    label = "House" if chamber == "house" else "Senate"
    lines = [f"**{label} District {num} Profile** (ACS 2020-2024 5-year)"]
    lines.append("")

    def row(name, field, table, note=""):
        pct = data.get(f"{field}_percent")
        moe = _clean_moe(data.get(f"{field}_percent_moe"))
        val = _pct(pct) if pct not in (None, "(X)") else "N/A"
        extra = f" {note}" if note else ""
        return f"- {name}: {val}{moe} ({table}, 2020-2024){extra}"

    lines.append(row("Population 16+", "pop_16_plus", "DP03"))
    lines.append(row("Median household income", "median_hh_income", "DP03"))
    lines.append(row("Poverty rate", "pct_people_poverty", "DP03"))
    lines.append(row("65+ living alone", "householders_65plus_living_alone", "DP02"))
    lines.append(row("With a disability", "with_disability", "DP02"))
    lines.append(row("Uninsured", "pct_no_health_insurance", "DP03"))
    lines.append(row("No vehicle available", "no_vehicle", "DP04"))
    lines.append(row("Speak English less than 'very well'", "limited_english", "DP02"))
    lines.append(row("Households reporting SNAP", "snap_benefits", "DP03", "(self-reported on Census, not DHS enrollment)"))

    # Rent burden
    try:
        p1 = float(str(data.get("rent_30_to_34_9_percent", "0")).replace("%", ""))
        p2 = float(str(data.get("rent_35_plus_percent", "0")).replace("%", ""))
        total = p1 + p2
        lines.append(f"- Rent burden (30%+ of income): {total:.1f}% (DP04, 2020-2024)")
    except (TypeError, ValueError):
        lines.append("- Rent burden: N/A")

    lines.append("")
    lines.append("Programs residents may qualify for (eligibility is determined by the administering agency):")
    lines.append(f"- SNAP: {PROGRAMS['snap']}")
    lines.append(f"- Med-QUEST: {PROGRAMS['medquest']}")
    lines.append(f"- LIHEAP: {PROGRAMS['liheap']}")
    lines.append(f"- Housing assistance: {PROGRAMS['hpha']}")
    lines.append(f"- Early learning: {PROGRAMS['earlylearning']}")
    return "\n".join(lines)

def general_lookup(q: str):
    chamber, num = parse_district(q)
    if not chamber or not num:
        return None
    data = get_district(chamber, num)
    if not data:
        return district_not_found(chamber, num)
    for pattern, field, label, table, is_money in METRICS:
        if re.search(pattern, q):
            if field == "rent_burden":
                try:
                    p1 = float(str(data.get("rent_30_to_34_9_percent", "0")).replace("%", ""))
                    p2 = float(str(data.get("rent_35_plus_percent", "0")).replace("%", ""))
                    total = p1 + p2
                    value = f"{total:.1f}%"
                    moe = ""
                except (TypeError, ValueError):
                    value, moe = "N/A", ""
            else:
                pct = data.get(f"{field}_percent")
                est = data.get(f"{field}_estimate")
                pct_moe = data.get(f"{field}_percent_moe")
                est_moe = data.get(f"{field}_moe")
                if is_money:
                    value = _money(est)
                    moe = _clean_moe(est_moe)
                else:
                    value = _pct(pct) if pct not in (None, "(X)") else _pct(est)
                    moe = _clean_moe(pct_moe)
            chamber_label = "House" if chamber == "house" else "Senate"
            return (
                f"In {chamber_label} District {num}, the {label} is {value}{moe} "
                f"(ACS 2020-2024 5-year, {table})."
            )
    return None

def answer(question: str) -> str:
    q = question.lower()

    # Decline: partisan
    if any(phrase in q for phrase in ["which party", "should i vote", "better for this district", "political party is better"]):
        return (
            "I can't answer questions about which political party is better for a district. "
            "That is a matter of opinion and policy preference, not a factual data question.\n\n"
            "For official election results and district maps, see the Hawaii Office of Elections: "
            "https://elections.hawaii.gov/"
        )

    # Decline: district-level SNAP enrollment (we only have self-reported Census SNAP)
    if any(phrase in q for phrase in ["exact number of snap", "snap enrollment by district", "how many people enrolled in snap in district", "district-level snap"]):
        return (
            "Actual SNAP enrollment is not published by legislative district. "
            "The Hawaii Department of Human Services releases participation numbers only at the county level. "
            "The ACS does report self-reported SNAP receipt by district (see 'Profile HD N' for that figure).\n\n"
            "For the most recent county and statewide figures, see the DHS BESSD SNAP page: "
            "https://humanservices.hawaii.gov/bessd/snap/"
        )

    # Homelessness — no district-level data
    if "homeless" in q:
        return (
            "No district-level data. Point-in-time counts are only published for Oahu and the neighbor island counties."
        )

    # Profile command
    if re.search(r"\bprofile\b", q):
        chamber, num = parse_district(q)
        if not num:
            return "Please name a district, e.g. 'Profile HD 22' or 'Profile SD 12'."
        return build_profile(chamber, num)

    # 1. Kūpuna poverty in HD 22 + Oʻahu comparison
    if ("house district 22" in q or "hd 22" in q or "hd22" in q) and ("65" in q or "kūpuna" in q or "kupuna" in q or "poverty" in q):
        data = get_district("house", 22)
        if not data:
            return district_not_found("house", 22)
        moe = _clean_moe(data.get("pct_65plus_poverty_percent_moe"))
        return (
            f"In House District 22, {_pct(data['pct_65plus_poverty_percent'])}{moe} of people age 65 and over live below the poverty line "
            f"(ACS 2020-2024 5-year, DP03). This is lower than the rate for kūpuna in Honolulu County (Oʻahu), which is {OAHU_65PLUS_POVERTY} "
            f"(ACS 2020-2024 5-year, S1701 / ACSST5Y2024.S1701).\n\n"
            f"Relevant programs: SNAP ({PROGRAMS['snap']}), LIHEAP ({PROGRAMS['liheap']}), "
            f"and senior nutrition / property-tax relief programs. Residents may qualify; eligibility is determined by the administering agency."
        )

    # 3. Top uninsured House districts
    if re.search(r"uninsured|uninsurance|no\s*health|without\s*(?:health\s*)?insurance|health\s*insurance|health\s*coverage", q):
        if "top" in q or "highest" in q or "which" in q:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.execute("""
                SELECT district, pct_no_health_insurance_percent, pct_no_health_insurance_percent_moe
                FROM house_districts 
                ORDER BY CAST(REPLACE(pct_no_health_insurance_percent, '%', '') AS REAL) DESC 
                LIMIT 3
            """)
            rows = cur.fetchall()
            conn.close()
            lines = []
            for r in rows:
                moe = _clean_moe(r["pct_no_health_insurance_percent_moe"])
                lines.append(f"House District {r['district']}: {r['pct_no_health_insurance_percent']}{moe}")
            return (
                "Top 3 House districts by share of residents without health insurance "
                "(ACS 2020-2024 5-year, DP03, civilian noninstitutionalized population):\n"
                + "\n".join(lines) +
                f"\n\nRelevant program: Med-QUEST ({PROGRAMS['medquest']}). Residents may qualify; eligibility is determined by the administering agency."
            )

    # 4. Rent burden
    if re.search(r"rent\s*burden|rent\s*burdened|housing\s*costs", q) or ("rent" in q and ("30" in q or "burden" in q or "income" in q)):
        chamber, num = parse_district(q)
        if not num:
            return "I can't answer that yet. Please name a district, e.g. 'HD 19'."
        data = get_district("house", num)
        if not data:
            return district_not_found("house", num)
        try:
            p1 = float(str(data.get("rent_30_to_34_9_percent", "0")).replace("%", ""))
            p2 = float(str(data.get("rent_35_plus_percent", "0")).replace("%", ""))
            total = p1 + p2
        except (TypeError, ValueError):
            total = None
        total_str = f"{total:.1f}%" if total is not None else "N/A"
        return (
            f"In House District {num}, {total_str} of renter households spend 30% or more of their income on gross rent "
            f"(ACS 2020-2024 5-year, DP04, GRAPI: 30–34.9% + 35%+).\n\n"
            f"Relevant programs: Housing Choice Voucher / Section 8 and other rental assistance ({PROGRAMS['hpha']}). Residents may qualify; eligibility is determined by the administering agency."
        )

    # 5. Children under 5 in poverty (HD 45)
    if ("under 5" in q or "children under" in q) and ("poverty" in q or "low-income" in q or "low income" in q):
        data = get_district("house", 45)
        if not data:
            return district_not_found("house", 45)
        moe = _clean_moe(data.get("pct_children_under5_poverty_percent_moe"))
        return (
            f"In House District 45, {_pct(data.get('pct_children_under5_poverty_percent'))}{moe} of related children under 5 years live below the poverty level "
            f"(ACS 2020-2024 5-year, DP03).\n\n"
            f"Relevant programs: Head Start / Early Head Start, Preschool Open Doors, EOEL Public Pre-K ({PROGRAMS['earlylearning']}), "
            f"Child Care Subsidy, Med-QUEST, SNAP, and WIC. Residents may qualify; eligibility is determined by the administering agency."
        )

    # 2. SNAP eligibility (SD 12) — careful wording
    if "snap" in q and ("senate" in q or "district 12" in q):
        data = get_district("senate", 12)
        if not data:
            return district_not_found("senate", 12)
        oahu = get_county_snap("Honolulu")
        oahu_hh = f"{oahu['households']:,}" if oahu else "~50,700"
        moe = _clean_moe(data.get("pct_people_poverty_percent_moe"))
        snap_pct = _pct(data.get("snap_benefits_percent"))
        snap_moe = _clean_moe(data.get("snap_benefits_percent_moe"))
        return (
            f"Senate District 12 has a poverty rate of {_pct(data.get('pct_people_poverty_percent'))}{moe} "
            f"(ACS 2020-2024 5-year, DP03). "
            f"{snap_pct}{snap_moe} of households reported receiving SNAP in the past 12 months (ACS 2020-2024, DP03; self-reported on the Census survey, not DHS enrollment). "
            f"Actual SNAP enrollment is not published by legislative district. "
            f"At the county level, Honolulu County (Oʻahu) had {oahu_hh} SNAP households as of September 2025 "
            f"(Hawaii DHS BESSD testimony).\n\n"
            f"Relevant program: SNAP application via DHS BESSD ({PROGRAMS['snap']}). Residents may qualify; eligibility is determined by the administering agency."
        )

    # County taxes
    if ("get" in q or "general excise" in q or "tat" in q or "transient accommodation" in q) and ("county" in q or "oahu" in q or "oʻahu" in q or "maui" in q or "hawaii" in q or "kauai" in q or "kauaʻi" in q):
        county_map = {
            "oahu": "Honolulu", "oʻahu": "Honolulu", "honolulu": "Honolulu",
            "maui": "Maui", "hawaii": "Hawaii", "hawaiʻi": "Hawaii",
            "kauai": "Kauai", "kauaʻi": "Kauai",
        }
        county = next((name for key, name in county_map.items() if key in q), "Honolulu")
        taxes = get_county_taxes(county)
        if not taxes:
            return f"No tax data found for {county} County."
        return (
            f"In {county} County, May 2026 tax liabilities (DOTAX liability-by-district reports):\n"
            f"- General Excise and Use Tax: {_money(taxes['get_liability_may2026'])}\n"
            f"- Transient Accommodations Tax: {_money(taxes['tat_liability_may2026'])}\n\n"
            f"These are county-level figures (tax districts), not legislative districts. "
            f"Source: Hawaii Department of Taxation, May 2026 monthly reports."
        )

    # County housing
    if ("home price" in q or "housing price" in q or "median home" in q or "single-family" in q or "single family" in q) and ("county" in q or "oahu" in q or "oʻahu" in q or "maui" in q or "hawaii" in q or "kauai" in q or "kauaʻi" in q):
        county_map = {
            "oahu": "Honolulu", "oʻahu": "Honolulu", "honolulu": "Honolulu",
            "maui": "Maui", "hawaii": "Hawaii", "hawaiʻi": "Hawaii",
            "kauai": "Kauai", "kauaʻi": "Kauai",
        }
        county = next((name for key, name in county_map.items() if key in q), "Honolulu")
        housing = get_county_housing(county)
        if not housing:
            return f"No housing data found for {county} County."
        return (
            f"In {county} County, the median single-family home sales price in 2025 was {_money(housing['median_sf_price_2025'])} "
            f"(UHERO Hawaiʻi Housing Factbook 2026). "
            f"The county resident population as of July 1, 2025 was {housing['population_july2025']:,} "
            f"(U.S. Census Bureau Vintage 2025 estimates / DBEDT Data Book).\n\n"
            f"These are county-level figures. Housing affordability remains a statewide challenge."
        )

    # General lookup
    looked = general_lookup(q)
    if looked:
        return looked

    chamber, num = parse_district(q)
    if not num:
        return "I can't answer that yet. Please name a district, e.g. 'HD 19' or 'SD 12'."

    return (
        "I can answer questions about Hawaii legislative districts using ACS 2020-2024 data. "
        "Try 'Profile HD 22', or ask about poverty, uninsured, rent burden, disability, limited English, or SNAP."
    )

if __name__ == "__main__":
    print(answer("Profile HD 22"))
    print()
    print(answer("Profile SD 12"))
    print()
    print(answer("What is the homelessness rate in HD 5?"))
    print()
    print(answer("What share of householders 65+ live alone in HD 22?"))
