# Sources

Every source Know Your District draws on (28 in all). Generated from `kyd/data/sources.csv` by `kyd/etl/make_sources_md.py`; the app's Sources tab shows the same list. Figure-level citations (source, vintage, method, margin of error) travel with every number through the API.

## Demographics

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [ACS 5-year Data Profiles DP02–DP05, state legislative districts](https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/) | U.S. Census Bureau (tabulated by Hawaiʻi State Data Center / DBEDT) | Population, age, income, poverty, housing, health insurance, disability, language, veterans, broadband, with margins of error | 2020–2024 5-year | Overview, Map, Compare, Rankings, Agent | 2026-11 |
| [ACS S1701 Poverty Status](https://data.census.gov/table/ACSST5Y2024.S1701) | U.S. Census Bureau | Poverty by age, and the 125/138/150/185/200% of poverty ladder used for program eligibility proxies | 2020–2024 5-year | Programs, Cross-program estimates, Rankings | 2026-11 |
| [ACS S2201 Food Stamps/SNAP](https://data.census.gov/table/ACSST5Y2024.S2201) | U.S. Census Bureau | Households receiving SNAP, and SNAP households with children, someone 60+, or someone with a disability | 2020–2024 5-year | Overview, Programs, SNAP gap | 2026-11 |

## Employment

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [ACS B23025 / B23001 / C23002A–I / B23006](https://www.census.gov/programs-surveys/acs/data/summary-file.html) | U.S. Census Bureau (summary file) | Unemployment by sex, age, race/ethnicity and education for districts, counties and the state | 2020–2024 5-year | Programs (Unemployment by group) | 2026-11 |
| [Local Area Unemployment Statistics by census tract and county](https://dbedt.hawaii.gov/economic/labor/) | Hawaiʻi DBEDT Research & Economic Analysis Division / DLIR | Labor force, unemployed and unemployment rate; county trend 2014–2025 | 2025 annual average | Programs (Unemployment), Rankings | 2026-11 |

## Programs

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [DHS Databook 2025](https://humanservices.hawaii.gov/wp-content/uploads/2026/03/DHS-Databook-2025.pdf) | Hawaiʻi Department of Human Services | Med-QUEST, TANF and SNAP caseloads by island; TANF reach by race; Census poverty estimates | SFY 2025 | Programs (island context) | 2026-11 |
| [BESSD monthly SNAP caseload summary](https://humanservices.hawaii.gov/bessd/snap/) | Hawaiʻi DHS Benefit Employment & Support Services Division | SNAP households and persons by county and island office | SFY 2026 (latest month 2026-02) | Programs (county SNAP) | 2026-11 |
| [Med-QUEST enrollment report](https://medquest.hawaii.gov/api/media/file/Website%20Enrollment%20Report%202026%2020261106.pdf) | Hawaiʻi DHS Med-QUEST Division | Medicaid enrollment by island | November 2026 | Programs | 2026-11 |
| [HCNP October Data](https://hcnp.hawaii.gov/wp-content/uploads/2026/01/October-Data-2026-SY25-26.pdf) | Hawaiʻi Child Nutrition Programs (HIDOE) | Free and reduced-price meal eligibility by school, rolled up to districts by school location (charter schools excluded) | SY2025-26 | Programs, Cross-program estimates | 2026-11 |

## Education

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [Smarter Balanced and HSA Science results](https://hawaiipublicschools.org/academics/types-of-testing/) | Hawaiʻi State Department of Education | ELA, math and science proficiency by school, rolled up to districts by school location (charter schools excluded) | SY2024-25 | Programs (Test scores) | 2026-11-15 |

## Housing

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [Picture of Subsidized Households](https://www.huduser.gov/portal/datasets/assthsg.html) | U.S. Department of Housing and Urban Development | Subsidized units and residents by program (vouchers, public housing, project-based Section 8, 202/811) by census tract | 2025 (as of 2025-12-31) | Programs (HUD housing), Map | 2026-11 |

## Equity

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [Low Income and Disadvantaged Communities (LIDAC)](https://geodata.hawaii.gov/arcgis/rest/services/HumanHealthSafety/MapServer/22) | Hawaiʻi Statewide GIS Program / Hawaiʻi Climate Commission | Share of residents in LIDAC and most-vulnerable LIDAC block groups | 2026 | Overview, Map, Rankings | 2026-11 |

## Safety

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [HPD Annual Reports (ESTIMATE)](https://www.honolulupd.org/information/annual-report/) | Honolulu Police Department | Index, violent and property offenses by beat, allocated to districts (Oʻahu only; beat lines traced from report maps) | 2017–2025 | Programs (Crime), Map, Rankings | 2026-11 |

## Program rules

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [SNAP income and allotment standards](https://www.fns.usda.gov/snap/allotment/cola) | USDA Food and Nutrition Service | Hawaiʻi SNAP cost-of-living adjustments and allotments (Hawaiʻi uses 200% of poverty, broad-based categorical eligibility) | FY2026 | Programs, Cross-program estimates | 2026-11 |
| [Med-QUEST MAGI income standards](https://medquest.hawaii.gov/api/media/file/2026%20PPDO%20MAGI%20and%20MAGI-Excepted%20Income%20Standards%20CHART.pdf) | Hawaiʻi DHS Med-QUEST Division | Medicaid income limits (138% of poverty for adults) | 2026 | Cross-program estimates | 2026-11 |
| [WIC income eligibility guidelines](https://www.federalregister.gov/documents/2026/04/29/2026-08323/special-supplemental-nutrition-program-for-women-infants-and-children-wic-income-eligibility-guidelines) | USDA FNS (Federal Register) | WIC income limit (185% of poverty) and adjunctive eligibility | 2026–27 | Cross-program estimates | 2026-11 |
| [Lifeline eligibility (47 CFR 54.409)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-54/subpart-E/section-54.409) | Federal Communications Commission (eCFR) | Lifeline eligibility via SNAP/Medicaid/SSI or 135% of poverty | current | Cross-program estimates | 2026-11 |
| [LIHEAP / H-HEAP model plan](https://humanservices.hawaii.gov/wp-content/uploads/2026/09/H-HEAP-Model-Plan-for-DHS-Website.pdf) | Hawaiʻi DHS BESSD | Energy assistance eligibility and benefit rules | FFY2027 | Cross-program estimates | 2026-11 |
| [TANF state plan and financial assistance standards](https://humanservices.hawaii.gov/wp-content/uploads/2026/10/Hawaii_Proposed_TANF_State_Plan_Effective_20261001-Watermarked.pdf) | Hawaiʻi DHS BESSD | TANF/TAONF and General Assistance standards | 2026 | Programs | 2026-11 |
| [HUD income limits](https://www.huduser.gov/portal/datasets/il.html#documents_2026) | U.S. Department of Housing and Urban Development | Section 8 income limits by county | FY2026 | Programs | 2026-11 |
| [Earned Income Tax Credit](https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit-eitc) | IRS and Hawaiʻi Department of Taxation | Federal EITC tables and Hawaiʻi EITC claims | 2024–2025 | Programs | 2026-11 |
| [SSI recipients by state](https://www.ssa.gov/policy/docs/statcomps/ssi_sc/2025/hi.html) | Social Security Administration | SSI recipients in Hawaiʻi by county | 2025 | Programs | 2026-11 |

## Geography

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [2022 State House and Senate district boundaries](https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer) | Hawaiʻi Statewide GIS Program / State Office of Elections | Official district lines (AdminBnd layers 33 and 34) used for the map and all crosswalks | 2022 reapportionment | Map, every district figure | 2026-11 |
| [2020 Census blocks and block groups](https://geodata.hawaii.gov/arcgis/rest/services/Census/MapServer) | U.S. Census Bureau via Hawaiʻi Statewide GIS Program | Population weights for the tract, block-group, beat and school crosswalks | 2020 Census | Crosswalks | 2026-11 |
| [2020 Census Designated Places and ZIP Code Tabulation Areas](https://geodata.hawaii.gov/arcgis/rest/services/Census/MapServer) | U.S. Census Bureau via Hawaiʻi Statewide GIS Program | Place-name and ZIP lookups that tell the agent which districts cover a place | 2020 Census | Agent (place and ZIP questions) | 2026-11 |
| [Legislator roster](https://www.capitol.hawaii.gov/) | Hawaiʻi State Office of Elections and Hawaiʻi State Legislature | Representative and senator for each district | 2026 session | Map, Overview | 2026-11 |

## Basemap

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [World Imagery and ArcGIS Maps SDK](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9) | Esri | Satellite basemap tiles and map rendering | current | Map | 2026-11 |

## Health

| Source | Publisher | What it provides | Vintage | Used in | Accessed |
|---|---|---|---|---|---|
| [Births and deaths by community of residence (Hawaiʻi-IBIS), allocated to districts (ESTIMATE)](https://hhdw.org/report/) | Hawaiʻi Department of Health, Hawaii Health Data Warehouse | Live births and all-cause deaths 2000–2024, allocated to 2022 districts by 2020 Census block population; 2020–2024 averages and crude rates | 2000–2024 (updated 2026-01-05) | Programs (Births and deaths), Overview (add indicator), Agent | 2026-11-15 |
