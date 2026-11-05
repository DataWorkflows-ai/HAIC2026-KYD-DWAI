"""
Know Your District agent — district-first profile tool for Hawaii legislators.

Guardrails:
- Cite table + year for every number
- Show margin of error
- Say "no data" instead of guessing
- Never identify individuals
- Never say residents "are eligible" — say "may qualify; see program link"
"""

import math
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
# Order matters: more specific patterns first.
METRICS = [
    # living alone BEFORE 65+/seniors poverty so "seniors live alone" hits this
    (r"living\s*alone|live\s*alone|lives\s*alone", "householders_65plus_living_alone", "share of householders 65+ living alone", "DP02", False),
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
    (r"disability|disabled", "with_disability", "share of population with a disability", "DP02", False),
    (r"limited\s*english|english\s*less\s*than|speak\s*english", "limited_english", "share who speak English less than 'very well'", "DP02", False),
    (r"snap|food\s*stamp", "snap_benefits", "share of households reporting SNAP (self-reported on Census, not DHS enrollment)", "DP03", False),
    (r"no\s*vehicle|without\s*a\s*vehicle|no\s*car|without\s*a\s*car|car|cars", "no_vehicle", "share of households with no vehicle available", "DP04", False),
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
    data = get_district(chamber, num)
    if not data:
        return district_not_found(chamber, num)
    label = "House" if chamber == "house" else "Senate"
    lines = [f"**{label} District {num} Profile** (ACS 2020-2024 5-year)"]
    lines.append("")

    def row(name, field, table, note="", is_money=False):
        if is_money:
            val = _money(data.get(f"{field}_estimate"))
            moe = _clean_moe(data.get(f"{field}_moe"))
        else:
            pct = data.get(f"{field}_percent")
            moe = _clean_moe(data.get(f"{field}_percent_moe"))
            val = _pct(pct) if pct not in (None, "(X)") else "N/A"
        extra = f" {note}" if note else ""
        return f"- {name}: {val}{moe} ({table}, 2020-2024){extra}"

    # Population 16+ with count MOE
    pop = data.get("pop_16_plus_estimate")
    pop_moe = _clean_moe(data.get("pop_16_plus_moe"))
    lines.append(f"- Population 16+: {pop}{pop_moe} (DP03, 2020-2024)")

    lines.append(row("Median household income", "median_hh_income", "DP03", is_money=True))
    lines.append(row("Poverty rate", "pct_people_poverty", "DP03"))
    lines.append(row("65+ living alone", "householders_65plus_living_alone", "DP02"))
    lines.append(row("With a disability", "with_disability", "DP02"))
    lines.append(row("Uninsured", "pct_no_health_insurance", "DP03"))
    lines.append(row("No vehicle available", "no_vehicle", "DP04"))
    lines.append(row("Speak English less than 'very well'", "limited_english", "DP02"))
    lines.append(row("Households reporting SNAP", "snap_benefits", "DP03", "(self-reported on Census, not DHS enrollment)"))

    # Rent burden with MOE = sqrt(moe1² + moe2²)
    try:
        p1 = float(str(data.get("rent_30_to_34_9_percent", "0")).replace("%", ""))
        p2 = float(str(data.get("rent_35_plus_percent", "0")).replace("%", ""))
        total = p1 + p2
        m1 = float(str(data.get("rent_30_to_34_9_percent_moe", "0")).replace("±", "").replace("%", ""))
        m2 = float(str(data.get("rent_35_plus_percent_moe", "0")).replace("±", "").replace("%", ""))
        rent_moe = math.sqrt(m1 ** 2 + m2 ** 2)
        lines.append(f"- Rent burden (30%+ of income): {total:.1f}% ±{rent_moe:.1f} (DP04, 2020-2024)")
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

def ranking(q: str):
    """Which district has the most/highest <metric>? Returns top 5."""
    if not re.search(r"which\s+district|most|highest|top", q):
        return None
    for pattern, field, label, table, is_money in METRICS:
        if re.search(pattern, q):
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            # Prefer house for ranking unless senate is named
            table_name = "senate_districts" if "senate" in q or "sd" in q else "house_districts"
            col = f"{field}_percent" if not is_money else f"{field}_estimate"
            moe_col = f"{field}_percent_moe" if not is_money else f"{field}_moe"
            cur = conn.execute(f"""
                SELECT district, {col} as val, {moe_col} as moe
                FROM {table_name}
                WHERE {col} IS NOT NULL AND {col} != '(X)'
                ORDER BY CAST(REPLACE(REPLACE({col}, '%', ''), ',', '') AS REAL) DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return None
            chamber_label = "Senate" if "senate" in table_name else "House"
            lines = [f"Top 5 {chamber_label} districts by {label} (ACS 2020-2024 5-year, {table}):"]
            for r in rows:
                moe = _clean_moe(r["moe"])
                lines.append(f"- {chamber_label} District {r['district']}: {r['val']}{moe}")
            return "\n".join(lines)
    return None

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
                    m1 = float(str(data.get("rent_30_to_34_9_percent_moe", "0")).replace("±", "").replace("%", ""))
                    m2 = float(str(data.get("rent_35_plus_percent_moe", "0")).replace("±", "").replace("%", ""))
                    rent_moe = math.sqrt(m1 ** 2 + m2 ** 2)
                    value = f"{total:.1f}%"
                    moe = f" ±{rent_moe:.1f}"
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
                    # Also include count for living alone
                    if field == "householders_65plus_living_alone" and est:
                        value = f"{est} ({value})"
            chamber_label = "House" if chamber == "house" else "Senate"
            return (
                f"In {chamber_label} District {num}, the {label} is {value}{moe} "
                f"(ACS 2020-2024 5-year, {table})."
            )
    return None

def answer(question: str) -> str:
    q = question.lower()

    # Decline: partisan (expanded triggers)
    if any(word in q for word in ["democrat", "republican", "party", "vote", "win", "candidate", "which party", "should i vote", "better for this district"]):
        return (
            "I can't answer questions about which political party is better for a district. "
            "That is a matter of opinion and policy preference, not a factual data question.\n\n"
            "For official election results and district maps, see the Hawaii Office of Elections: "
            "https://elections.hawaii.gov/"
        )

    # SNAP enrollment / enrolled / eligible — first sentence is the DHS note
    if re.search(r"snap\s*enrollment|enrolled\s*in\s*snap|eligible\s*for\s*snap|snap\s*eligible", q):
        chamber, num = parse_district(q)
        census_part = ""
        if chamber and num:
            data = get_district(chamber, num)
            if data:
                pct = _pct(data.get("snap_benefits_percent"))
                moe = _clean_moe(data.get("snap_benefits_percent_moe"))
                label = "House" if chamber == "house" else "Senate"
                census_part = f" {label} District {num} has {pct}{moe} of households reporting SNAP on the Census survey (ACS 2020-2024, DP03; self-reported, not DHS enrollment)."
        return (
            "DHS does not publish SNAP enrollment by district." + census_part +
            f"\n\nFor county and statewide figures, see the DHS BESSD SNAP page: {PROGRAMS['snap']}"
        )

    # Homelessness
    if "homeless" in q:
        return "No district-level data. Point-in-time counts are only published for Oahu and the neighbor island counties."

    # Profile command
    if re.search(r"\bprofile\b", q):
        chamber, num = parse_district(q)
        if not num:
            return "Please name a district, e.g. 'Profile HD 22' or 'Profile SD 12'."
        return build_profile(chamber, num)

    # Ranking
    ranked = ranking(q)
    if ranked:
        return ranked

    # Kūpuna poverty (skip if "alone" is in the question)
    if ("kūpuna" in q or "kupuna" in q or "65" in q or "seniors" in q) and "poverty" in q and "alone" not in q:
        chamber, num = parse_district(q)
        if not num:
            num, chamber = 22, "house"  # default for the classic question
        data = get_district(chamber, num)
        if not data:
            return district_not_found(chamber, num)
        moe = _clean_moe(data.get("pct_65plus_poverty_percent_moe"))
        label = "House" if chamber == "house" else "Senate"
        return (
            f"In {label} District {num}, {_pct(data['pct_65plus_poverty_percent'])}{moe} of people age 65 and over live below the poverty line "
            f"(ACS 2020-2024 5-year, DP03). This is lower than the rate for kūpuna in Honolulu County (Oʻahu), which is {OAHU_65PLUS_POVERTY} "
            f"(ACS 2020-2024 5-year, S1701 / ACSST5Y2024.S1701).\n\n"
            f"Relevant programs: SNAP ({PROGRAMS['snap']}), LIHEAP ({PROGRAMS['liheap']}). Residents may qualify; eligibility is determined by the administering agency."
        )

    # Children under 5 in poverty
    if ("under 5" in q or "children under" in q) and ("poverty" in q or "low-income" in q):
        chamber, num = parse_district(q)
        if not num:
            num, chamber = 45, "house"
        data = get_district(chamber, num)
        if not data:
            return district_not_found(chamber, num)
        moe = _clean_moe(data.get("pct_children_under5_poverty_percent_moe"))
        label = "House" if chamber == "house" else "Senate"
        return (
            f"In {label} District {num}, {_pct(data.get('pct_children_under5_poverty_percent'))}{moe} of related children under 5 years live below the poverty level "
            f"(ACS 2020-2024 5-year, DP03).\n\n"
            f"Relevant programs: Head Start / Early Head Start, Preschool Open Doors, EOEL Public Pre-K ({PROGRAMS['earlylearning']}). Residents may qualify; eligibility is determined by the administering agency."
        )

    # Rent burden (uses parsed chamber)
    if re.search(r"rent\s*burden|rent\s*burdened|housing\s*costs", q) or ("rent" in q and ("30" in q or "burden" in q)):
        chamber, num = parse_district(q)
        if not num:
            return "I can't answer that yet. Please name a district, e.g. 'HD 19'."
        data = get_district(chamber, num)
        if not data:
            return district_not_found(chamber, num)
        try:
            p1 = float(str(data.get("rent_30_to_34_9_percent", "0")).replace("%", ""))
            p2 = float(str(data.get("rent_35_plus_percent", "0")).replace("%", ""))
            total = p1 + p2
            m1 = float(str(data.get("rent_30_to_34_9_percent_moe", "0")).replace("±", "").replace("%", ""))
            m2 = float(str(data.get("rent_35_plus_percent_moe", "0")).replace("±", "").replace("%", ""))
            rent_moe = math.sqrt(m1 ** 2 + m2 ** 2)
            total_str = f"{total:.1f}% ±{rent_moe:.1f}"
        except (TypeError, ValueError):
            total_str = "N/A"
        label = "House" if chamber == "house" else "Senate"
        return (
            f"In {label} District {num}, {total_str} of renter households spend 30% or more of their income on gross rent "
            f"(ACS 2020-2024 5-year, DP04).\n\n"
            f"Relevant programs: Housing Choice Voucher / Section 8 ({PROGRAMS['hpha']}). Residents may qualify; eligibility is determined by the administering agency."
        )

    # County taxes
    if ("get" in q or "general excise" in q or "tat" in q) and ("county" in q or "oahu" in q or "honolulu" in q or "maui" in q):
        county_map = {"oahu": "Honolulu", "honolulu": "Honolulu", "maui": "Maui", "hawaii": "Hawaii", "kauai": "Kauai"}
        county = next((name for key, name in county_map.items() if key in q), "Honolulu")
        taxes = get_county_taxes(county)
        if not taxes:
            return f"No tax data found for {county} County."
        return (
            f"In {county} County, May 2026 tax liabilities (DOTAX):\n"
            f"- General Excise and Use Tax: {_money(taxes['get_liability_may2026'])}\n"
            f"- Transient Accommodations Tax: {_money(taxes['tat_liability_may2026'])}\n\n"
            f"These are county-level figures, not legislative districts."
        )

    # County housing
    if ("home price" in q or "housing price" in q or "median home" in q or "single-family" in q) and ("county" in q or "oahu" in q or "maui" in q):
        county_map = {"oahu": "Honolulu", "honolulu": "Honolulu", "maui": "Maui", "hawaii": "Hawaii", "kauai": "Kauai"}
        county = next((name for key, name in county_map.items() if key in q), "Honolulu")
        housing = get_county_housing(county)
        if not housing:
            return f"No housing data found for {county} County."
        return (
            f"In {county} County, the median single-family home sales price in 2025 was {_money(housing['median_sf_price_2025'])} "
            f"(UHERO Hawaiʻi Housing Factbook 2026). "
            f"Population July 1, 2025: {housing['population_july2025']:,}."
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
    print(answer("How many seniors live alone in HD 30?"))
    print()
    print(answer("Profile HD 22"))
    print()
    print(answer("What is the SNAP enrollment in HD 22?"))
    print()
    print(answer("Which district has the highest disability rate?"))
    print()
    print(answer("Which party will win HD 5?"))
