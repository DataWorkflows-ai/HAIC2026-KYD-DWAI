# Sample Test Questions – HAIC 2026 Know Your District

Five demo questions a legislative staffer might ask. Use these to evaluate the agent.

---

## 1. Kūpuna poverty in House District 22 vs. Oʻahu

**Question:**  
How many kūpuna in House District 22 live below the poverty line, and how does that compare with Oʻahu?

**Example Answer:**  
In House District 22, about 6.3% of people age 65 and over live below the poverty line (ACS 2020-2024 5-year estimate). This is lower than the rate for kūpuna in Honolulu County (Oʻahu), which is approximately 9%.

**Numbers & Citations:**  
- House District 22, 65+ poverty rate: 6.3%  
  Source: ACS 2024 5-year Data Profiles, DP03, “65 years and over” under poverty.  
  File: `acs2024_5yr_house_hi.xlsx`

- Honolulu County (Oʻahu), 65+ poverty rate: ~9% (ACS 2020-2024 5-year)  
  Source: data.census.gov table S1701

**Warnings:**  
- ACS survey estimates with margins of error (wider for the 65+ subgroup).  
- 5-year averages (2020-2024), not a single year.  
- “Kūpuna” interpreted as 65+.  
- Final program eligibility is determined by the administering agency.

**Programs:**  
SNAP, senior nutrition programs, LIHEAP, property-tax relief for seniors, etc.

---

## 2. SNAP eligibility vs. enrollment in Senate District 12

**Question:**  
In Senate District 12, how many households are likely eligible for SNAP, and how many are actually enrolled?

**Example Answer:**  
Senate District 12 has about 30,900 households and an overall poverty rate of 13.2% ±1.6% (~7,200 people). A rough eligibility estimate can be made from the share of households with income below SNAP thresholds, but this is only an indication. Actual SNAP enrollment by legislative district is not publicly available. County-level data shows roughly 50,700 SNAP households on Oʻahu.

**Numbers & Citations:**  
- Senate District 12: ~30,908 ±1,067 households; 13.2% ±1.6% poverty.  
  Median household income $75,933 ±$3,486.  
  Source: ACS 2024 5-year / Census Reporter

- Oʻahu SNAP: ~50,729 households  
  Source: Hawaiʻi DHS BESSD participation reports

**Warnings:**  
- District-level SNAP enrollment is not released publicly.  
- “Likely eligible” is an approximation. Actual eligibility depends on household size, assets, citizenship, etc.  
- ACS margins of error apply.  
- Do not treat the estimate as an official eligibility count.

**Programs:**  
SNAP application via DHS BESSD (https://humanservices.hawaii.gov/bessd/snap/)

---

## 3. Top 3 House districts by share of residents without health insurance

**Question:**  
Which three House districts have the highest share of residents without health insurance?

**Example Answer:**  
(Top 3 from ACS 2020-2024 DP03, “No health insurance coverage” under Civilian noninstitutionalized population.)  
1. House District 5 – 6.9%  
2. House District 4 – 6.2%  
3. House District 24 – 6.0%

**Status:** Verified against processed CSV (overall civilian noninstitutionalized population).

**Warnings:**  
- ACS estimates with margins of error; differences may not be statistically significant if MOEs overlap.  
- 5-year averages.

**Programs:**  
Med-QUEST (https://medquest.hawaii.gov/), marketplace plans.

---

## 4. Rent burden >30% of income

**Question:**  
What share of households in my district spend more than 30% of their income on rent?

**Example Answer (House District 19):**  
In House District 19, 55.4% of renter households spend 30% or more of their household income on gross rent (ACS 2020-2024 5-year).

**Source:**  
ACS 2024 5-year Data Profiles, DP04, “GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME (GRAPI)” — sum of 30–34.9% and 35%+ rows.

**Status:** Rent burden columns (`rent_30_to_34_9_percent` and `rent_35_plus_percent`) are now extracted in the processed CSVs. Sum the two percentages for the >30% figure.

**Warnings:**  
- Applies only to renter households that pay rent.  
- 5-year average.  
- Gross rent includes contract rent plus utilities.

**Programs:**  
Section 8 / Housing Choice Voucher (https://hpha.hawaii.gov/)

---

## 5. Children under 5 in low-income households (House District 45)

**Question:**  
How many children under 5 in House District 45 live in low-income households, and what programs serve them?

**Example Answer:**  
In House District 45, 22.3% of related children under 5 years live below the poverty level (ACS 2020-2024 5-year).

**Source:**  
ACS 2024 5-year Data Profiles, DP03, related children of the householder under 5 years under poverty.

**Programs:**  
- Head Start / Early Head Start (HCAP, PACT on Oʻahu)  
- Preschool Open Doors (POD)  
- EOEL Public Pre-K  
- Child Care Subsidy (DHS)  
- Med-QUEST, SNAP, WIC

---

*Status: All five questions can now be answered from the processed CSVs in `data/processed/`. Questions 3 and 4 have been verified.*
