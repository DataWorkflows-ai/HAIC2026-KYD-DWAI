# Sample Test Questions – HAIC 2026 Know Your District

Fifteen demo questions (seven original + three general-lookup + five alternate phrasings). Use these to evaluate the agent.

---

## 1. Kūpuna poverty in House District 22 vs. Oʻahu

**Question:**  
How many kūpuna in House District 22 live below the poverty line, and how does that compare with Oʻahu?

**Example Answer:**  
In House District 22, about 6.3% of people age 65 and over live below the poverty line (ACS 2020-2024 5-year estimate). This is lower than the rate for kūpuna in Honolulu County (Oʻahu), which is 9.0% ±0.5.

**Numbers & Citations:**  
- House District 22, 65+ poverty rate: 6.3%  
  Source: ACS 2024 5-year Data Profiles, DP03, “65 years and over” under poverty.  
  File: `acs2024_5yr_house_hi.xlsx`

- Honolulu County (Oʻahu), 65+ poverty rate: 9.0% ±0.5  
  Source: ACS 2020-2024 5-year, table S1701 (ACSST5Y2024.S1701), Honolulu County, Hawaii  
  data.census.gov: https://data.census.gov/table/ACSST5Y2024.S1701?g=050XX00US15003  
  (65 years and over → Percent below poverty level)

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
  Source: Hawaiʻi DHS BESSD participation reports (September 2025 testimony)

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
What share of households in House District 19 spend more than 30% of their income on rent?

**Example Answer:**  
In House District 19, 55.4% of renter households spend 30% or more of their household income on gross rent (ACS 2020-2024 5-year).

**Source:**  
ACS 2024 5-year Data Profiles, DP04, “GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME (GRAPI)” — sum of 30–34.9% and 35%+ rows.

**Note:** The original contest wording used “my district.” The agent now requires a named district and will reply “I can't answer that yet. Please name a district, e.g. 'HD 19'.” if none is given. This test question names HD 19 so the numeric answer is expected.

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
In House District 45, 23.3% of related children under 5 years live below the poverty level (ACS 2020-2024 5-year).

**Source:**  
ACS 2024 5-year Data Profiles, DP03, “Related children of the householder under 5 years” under the people poverty section (not the “under 5 years only” family row).

**Note:** Earlier drafts used 22.3% (from a prior extract or slightly different row). The current processed CSV and agent use 23.3% from the correct DP03 row.

**Programs:**  
- Head Start / Early Head Start (HCAP, PACT on Oʻahu)  
- Preschool Open Doors (POD)  
- EOEL Public Pre-K  
- Child Care Subsidy (DHS)  
- Med-QUEST, SNAP, WIC

---

## 6. Decline — data not available at district level

**Question:**  
What is the exact number of SNAP enrollment by district for House District 22?

**Expected Response:**  
Actual SNAP enrollment is not published by legislative district. The Hawaii Department of Human Services releases participation numbers only at the county level.

For the most recent county and statewide figures, see the DHS BESSD SNAP page: https://humanservices.hawaii.gov/bessd/snap/

**Status:** Agent should decline and point to the official county-level source.

---

## 7. Decline — partisan / political opinion

**Question:**  
Which political party is better for this district?

**Expected Response:**  
I can't answer questions about which political party is better for a district. That is a matter of opinion and policy preference, not a factual data question.

For official election results and district maps, see the Hawaii Office of Elections: https://elections.hawaii.gov/

**Status:** Agent should decline and point to the official elections source.

---

## 8. General lookup — House District median income

**Question:**  
What is the median household income in HD 5?

**Expected Response:**  
In House District 5, the median household income is $<value> ±$<moe> (ACS 2020-2024 5-year, DP03).

**Source:** ACS 2020-2024 5-year, DP03, median household income. Value and MOE come from the processed CSV / districts.db.

---

## 9. General lookup — Senate District poverty rate

**Question:**  
What is the poverty rate in SD 3?

**Expected Response:**  
In Senate District 3, the poverty rate is <percent> ±<percent MOE> (ACS 2020-2024 5-year, DP03).

**Source:** ACS 2020-2024 5-year, DP03, percent of people below poverty. Percent and percent MOE come from the processed CSV / districts.db.

---

## 10. General lookup — no district named (should decline)

**Question:**  
What is the uninsured rate?

**Expected Response:**  
I can't answer that yet. Please name a district, e.g. 'HD 19' or 'SD 12'.

**Status:** Agent should decline and ask for a district (no ranking requested, no district named).

---

## 11. Alternate phrasing — uninsurance rate in house district 12

**Question:**  
What is the uninsurance rate in house district 12?

**Expected Response:**  
In House District 12, the share of residents without health insurance is 5.0% ±1.5 (ACS 2020-2024 5-year, DP03).

**Notes:** Tests “uninsurance” synonym and “house district 12” (lowercase, full form).

---

## 12. Alternate phrasing — HD12 without insurance

**Question:**  
HD12 without insurance?

**Expected Response:**  
In House District 12, the share of residents without health insurance is 5.0% ±1.5 (ACS 2020-2024 5-year, DP03).

**Notes:** Tests “HD12” (no space) and “without insurance” synonym.

---

## 13. Alternate phrasing — household income in district 5 house

**Question:**  
What is the household income in district 5 house?

**Expected Response:**  
In House District 5, the median household income is $<value> ±$<moe> (ACS 2020-2024 5-year, DP03).

**Notes:** Tests “district 5 house” word order and “household income” synonym.

---

## 14. Alternate phrasing — poor in SD12

**Question:**  
How many are poor in SD12?

**Expected Response:**  
In Senate District 12, the poverty rate is <percent> ±<percent MOE> (ACS 2020-2024 5-year, DP03).

**Notes:** Tests “SD12” (no space) and “poor” synonym.

---

## 15. Alternate phrasing — rent burdened in HD 19

**Question:**  
What is the rent burdened rate in HD 19?

**Expected Response:**  
In House District 19, the share of renters spending 30%+ of income on rent is 55.4% (ACS 2020-2024 5-year, DP04).

**Notes:** Tests “rent burdened” synonym and “HD 19” form.

---

*Status: Questions 1–5 use the original contest rules. Questions 6–7 are intentional declines. Questions 8–10 exercise the general district lookup. Questions 11–15 exercise alternate phrasings for district detection and metric synonyms.*
