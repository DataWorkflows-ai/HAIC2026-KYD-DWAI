# Key Data Sources – HAIC Know Your District

## ACS 2020–2024 (5-year) Data Profiles – Legislative Districts

Confirmed in the repo. Both workbooks are the ACS 2020–2024 5-year estimates from the Hawaii State Data Center. Every figure is a sample-based estimate. Always read it with its margin of error. Do not treat a point estimate as exact.

### House Districts
- Excel (all House districts): https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_house_hi.xlsx
- Saved as `data/raw/acs2024_5yr_house_hi.xlsx`
- Sheets: DP02, DP03, DP04, DP05

### Senate Districts
- Excel (all Senate districts): https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_senate_hi.xlsx
- Saved as `data/raw/acs2024_5yr_senate_hi.xlsx`
- Sheets: DP02, DP03, DP04, DP05

### What the broad profiles cover

**DP02 — Selected Social Characteristics. House and Senate.**
Households by type, educational attainment, language spoken at home, veteran status, disability status of the civilian noninstitutionalized population, and computers and internet use. This is the broad profile for who lives in the district.

**DP05 — ACS Demographic and Housing Estimates. House and Senate.**
Population by age and sex, race, Hispanic or Latino origin, total housing units, and citizen voting-age population.

**DP03 and DP04** are also in both files. DP03 is economic characteristics (income, poverty, employment, health insurance). DP04 is housing, including gross rent as a percent of income.

### Subject tables (Hawaii, district level)

These are not sheets in the two Excel workbooks. They come from data.census.gov, filtered to Hawaii state legislative districts.

- **S1701** — Poverty Status in the Past 12 Months, by age, race/ethnicity (including Native Hawaiian/Pacific Islander alone), education, employment, and income-to-poverty ratios. Available for House and Senate districts (ACS 2020–2024 5-year). People below 130% of the federal poverty level are the SNAP eligibility proxy. Saved: `data/raw/S1701_senate_districts.json`, `data/raw/S1701_house_districts.json`.
  - https://data.census.gov/table/ACSST5Y2024.S1701
  - County example (Honolulu): https://data.census.gov/table/ACSST5Y2024.S1701?g=050XX00US15003
- **S1801** — Disability Characteristics, by type (hearing, vision, cognitive, ambulatory, self-care, independent living). Available for House and Senate.
  - https://data.census.gov/table/ACSST5Y2024.S1801
- **S2201** — Food Stamps/SNAP receipt by household type, age, race, and income. Available for House and Senate. This is the Census survey share, not DHS enrollment.
  - https://data.census.gov/table/ACSST5Y2024.S2201
  - Saved: `data/raw/S2201_senate_districts.json`, `data/raw/S2201_house_districts.json`
  - **How to read the percent columns (verified against Census API labels and Senate District 1):**
    - First row (Households / `_001`): `C04_001E` (“Percent households receiving food stamps/SNAP”) = share of **all** households that receive SNAP. This is the SNAP receipt rate.
    - Every other row: `C04_xxxE` = share of **SNAP-receiving households** that have that characteristic (e.g. “share of SNAP households with someone 60+”). This is **not** the receipt rate within the group.
    - Receipt rate within a group = that group’s SNAP count (`C03_xxxE`) ÷ that group’s total count (`C01_xxxE`).
    - `C02_xxxE` is the share of all households that have the characteristic; do not use it as a SNAP rate.
    - Example (Senate District 1): overall receipt rate `C04_001E` = 20.1%; share of SNAP households with someone 60+ `C04_002E` = 42.7%; receipt rate among 60+ households = 1,703 / 10,919 = 15.6% (calculated, not stored in `C04`).
    - Full mapping is in `SNAP_Analytical_Framework.md`.

- **S1810** — Disability Characteristics by type. Available for House and Senate districts. Adds disability by type (hearing, vision, cognitive, ambulatory, self-care, independent living). SNAP has special rules for elderly and disabled households, so this table supplies the disability context for the SNAP gap analysis.
  - Senate JSON: https://data.census.gov/api/access/data/table?g=040XX00US15%246100000&id=ACSST5Y2024.S1810
  - House JSON: https://data.census.gov/api/access/data/table?g=040XX00US15%246200000&id=ACSST5Y2024.S1810
  - Saved: `data/raw/S1810_senate_districts.json`, `data/raw/S1810_house_districts.json`

- **DP03** — Selected Economic Characteristics by district. Available for House and Senate. Adds employment, commute, occupation, industry, income, health insurance, and poverty — broader economic context for the district profile and program analysis.
  - Senate JSON: https://data.census.gov/api/access/data/table?g=040XX00US15%246100000&id=ACSDP5Y2024.DP03
  - House JSON: https://data.census.gov/api/access/data/table?g=040XX00US15%246200000&id=ACSDP5Y2024.DP03
  - Saved: `data/raw/DP03_senate_districts.json`, `data/raw/DP03_house_districts.json`
  - Also present as the DP03 sheet in the DBEDT Excel workbooks (`data/raw/acs2024_5yr_house_hi.xlsx`, `data/raw/acs2024_5yr_senate_hi.xlsx`).


- **S0103** — Population 65 Years and Over. Available for Senate. Withheld by the Census Bureau for most House districts, so do not treat a missing House cell as zero.
  - https://data.census.gov/table/ACSST5Y2024.S0103

### How to read and compare

- Always show the estimate with its margin of error, the table ID, and the ACS 2020–2024 5-year vintage.
- Hawaii draws legislative districts on permanent residents, not total Census population. District populations range from about 24,000 to 84,000. Compare districts with percents and rates, not raw counts.
- District numbers are the 2022 reapportionment districts. They are not comparable with earlier ACS vintages (pre-2022) or with 2020 Census redistricting tables.

### Honolulu County (Oʻahu) – comparison geography
- data.census.gov table S1701 (ACS 2024 5-year):
  https://data.census.gov/table/ACSST5Y2024.S1701?g=050XX00US15003
  - AGE → 65 years and over → Percent below poverty level

### Other ACS links
- Hawaii State Data Center ACS page: https://census.hawaii.gov/acs/acs-2024/
- Census Reporter (House District 22 example): https://censusreporter.org/profiles/62000US15022-state-house-district-22-hi/

### Key ACS Tables from Build Guide Done When list
These table IDs are called out in the build guide. Best retrieved via data.census.gov filtered to Hawaii State Legislative Districts (Upper/Lower Chamber), or already present in the House/Senate Excel Data Profiles above.

- **DP03** – Selected Economic Characteristics (income, poverty, employment, health insurance)
  - Already in the House & Senate Excels (DP03 sheet)
  - data.census.gov: https://data.census.gov/table?q=DP03 (filter to legislative districts)
- **S1701** – Poverty Status in the Past 12 Months (detailed by age, race/ethnicity, education, employment, income-to-poverty ratios)
  - Available for Hawaii House and Senate districts. Saved as `data/raw/S1701_senate_districts.json` and `data/raw/S1701_house_districts.json`.
  - data.census.gov: https://data.census.gov/table/ACSST5Y2024.S1701
- **B01001** – Sex by Age
  - data.census.gov: https://data.census.gov/table/ACSDT5Y2024.B01001
- **B17001** – Poverty Status in the Past 12 Months by Sex by Age
  - data.census.gov: https://data.census.gov/table/ACSDT5Y2024.B17001
- **B25070** – Gross Rent as a Percentage of Household Income
  - data.census.gov: https://data.census.gov/table/ACSDT5Y2024.B25070

## District profile join – sources to combine

These are the four sources for the district map plus who lives there, how the district voted, and statewide party-seat context. Recorded as they are supplied. More entries will be added.

### 1. GIS boundaries (map)

Parent service: Hawaiʻi Statewide GIS Program, AdminBnd MapServer. One service holds both chambers as separate polygon layers. Vintage is the 2022 reapportionment. Source: Hawaii State Office of Elections, March 2022.

- Service: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer
- Saved in the repo (retrieved 2026-11-05, not downloaded on each app run):
  - `data/boundaries/house_2022.geojson`
  - `data/boundaries/senate_2022.geojson`

**Senate — 25 polygon features** (AdminBnd layer 34, State Senate Districts 22)
- Geoportal: https://geoportal.hawaii.gov/datasets/8b86d4ce4cb04b988cc4cfd790405cb2
- GeoJSON: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/34/query?where=1%3D1&outFields=*&f=geojson
- Metadata: https://files.hawaii.gov/dbedt/op/gis/data/senate22.pdf
- Attributes:
  - `county` — county name
  - `senate_id` — numeric district ID, 1–25 (join key)
  - `senate_name` — full name, e.g. State Senate District 1
  - `senate_abbr` — abbreviation, e.g. 1ST SEN. DIST.
  - `state_senate` — short code, e.g. S01

**House — 51 polygon features** (AdminBnd layer 33, State House Districts 22)
- Geoportal / open data: https://opendata.hawaii.gov/dataset/hawaii-state-house-districts-2022
- ArcGIS item: https://www.arcgis.com/home/item.html?id=c2f8b485f2064ba1a117ececab301acd
- GeoJSON: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/33/query?where=1%3D1&outFields=*&f=geojson
- Metadata: https://files.hawaii.gov/dbedt/op/gis/data/house22.pdf
- Attributes:
  - `county` — county name
  - `house_id` — numeric district ID, 1–51 (join key)
  - `state_house` — district code, e.g. H01
  - `house_abbr` — abbreviation, e.g. 1ST REP. DIST.
  - `house_name` — full name, e.g. State House District 1

Use case: the map. Each polygon is the geographic footprint of one district. Join on district number (`house_id` or `senate_id`). One feature per district. Islands that belong to the same district are parts of that one feature, not separate district IDs.

**Election precincts — 250 polygon features** (AdminBnd layer 13, Election Precincts 2024)
- Source page: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/13
- Metadata: https://files.hawaii.gov/dbedt/op/gis/data/precincts.pdf
- Shapefile received 2026-11-14 (`Election_Precincts.shp` and sidecar files). Projection: NAD 1983 HARN UTM Zone 4N. Official service is also served in WGS84 from the geoportal.
- Source: State Office of Elections, May 2024. Voting precincts for the 2024 elections, used to place a point in a precinct.
- What it includes:
  - `dp` / `dpnum` — precinct ID (250 features; 247 distinct precinct IDs)
  - `dptype` — VBMO or ZEROPOP
  - `county` — HAWAII, KAUAI, MAUI, OAHU
  - `zeropop` — blank or yes
  - `ballottype` — ballot style, e.g. CD2-H01-S04-CC1
  - `us_house` — CD1 or CD2
  - `state_hous` — 2022 House district code, H01–H51 (all 51 present)
  - `state_sena` — 2022 Senate district code, S01–S25 (all 25 present)
  - `county_cou` — county council district, CC0–CC9
- Value to the project: this is the precinct-to-district crosswalk. Office of Elections results are published by precinct. `state_hous` and `state_sena` roll those precinct votes up to a House or Senate district so voting pattern can sit on the same district row as the ACS profile. County is on the same row.
- Spatial join: the current 2022 reapportionment polygons are the GeoJSON already in the repo (`house_2022.geojson`, `senate_2022.geojson`). Precincts (NAD83 HARN UTM Zone 4N) were reprojected to WGS84 and joined to those polygons on a representative point. Result on 2026-11-14: 250/250 precincts matched a House district and 250/250 matched a Senate district. The spatial district agreed with `state_hous` / `state_sena` on every precinct. Use the GeoJSON for the spatial join; the attribute codes are the same answer.
- Not in this file: total population, target population, and deviation from target. Those redistricting fields are not on the 2024 precinct layer. A separate reapportionment file would be needed for that analysis.

### 2. Census ACS profiles (who lives there)

Confirmed. Join on chamber plus district number to the 2022 boundary IDs.

- In the repo, both chambers: DP02 (households, education, language, veterans, disability, internet), DP05 (age/sex, race/ethnicity, housing units, citizen voting-age population), plus DP03 and DP04.
- Subject tables, not in the Excel files: S1801 and S1810 disability by type (House and Senate; S1810 adds hearing, vision, cognitive, ambulatory, self-care, independent living — relevant because SNAP has special rules for elderly/disabled), S2201 SNAP receipt (House and Senate), S1701 poverty detail (House and Senate; used as the SNAP eligibility proxy), S0103 age 65+ profile (Senate only; House withheld for most districts).
Use case: who lives in the district. Join to the 2022 boundary on district number. Always cite table, ACS 2020–2024 5-year vintage, and margin of error. Compare percents, not raw counts. Do not join these district numbers to pre-2022 ACS or 2020 Census redistricting tables.

### 3. Election results (voting pattern)

Use case: show how a district voted in 2022, by contest, district, and candidate. Join to the map on district number. These are official statewide summary totals, not a precinct rollup. They are recorded and not yet drawn on the map.

**Primary, August 13, 2022**
- Source: Office of Elections, Primary Election 2022 Statewide Summary Report 5.
- File: `data/processed/election_2022_primary_by_district.csv`
- Coverage: all 25 Senate and all 51 House districts.
- Layout: one row per contest, district, party ballot, and candidate. Blank and over votes kept.
- How to read it: Hawaii primary voters pick a party ballot. A Democratic total and a Republican total in the same district are not one combined district vote. Do not treat these as general-election results.

**General, November 8, 2022, final**
- Source: Office of Elections, General Election 2022 Statewide Final Summary Report.
- File: `data/processed/election_2022_general_by_district.csv`
- Coverage: 21 Senate contests and 42 House contests.
- Layout: one row per contest, district, and candidate, with party, votes, and percent. Blank and over votes kept. Candidates from different parties are in the same contest, so these are district-wide totals.
- Not printed in the report: Senate 3, 5, 19, 20 and House 1, 2, 7, 9, 10, 18, 23, 31, 33. Usually uncontested. A missing contest is not a zero-vote district.

### 4. Party membership trends (historical context)

Recorded from `DB2025_section08.numbers`, received 2026-11-14. Table 8.12, Party Membership of the State Legislature, 1987 to 2026.

- Source: Hawaii State Office of Elections records and the Hawaii State Legislature. Data Book 2025, Section 8.
- Data Book page: https://dbedt.hawaii.gov/economic/databook/
- What it is: seats held by party in the whole House and the whole Senate, one row per session year. Columns are total, Democrats, Republicans, and Other.
- Geography: statewide. No district number and no county. It does not join to a district row.
- Value to the project: historical context for the chamber. It sits beside the district profile. It is not a measure of how a district voted, and Hawaii does not register voters by party.
- Extracted to `data/processed/party_membership_legislature.csv` (34 House years, 34 Senate years).

### Join status (2026-11-14)

- GIS to ACS: joined on district number. 51 House and 25 Senate, all matched. County comes from the boundary file. Percents and margins of error kept. Table: `data/processed/district_profile_joined.csv`.
- Map footprint: each GeoJSON polygon is that district's geographic footprint. Joined on district number to the profile. Outputs: `data/boundaries/house_2022_joined.geojson` and `data/boundaries/senate_2022_joined.geojson`. Every feature has `district` plus its polygon. 51/51 House and 25/25 Senate matched.
- Election results: extracted by contest, district, and candidate. Join key is district number, same as the GeoJSON. Not yet attached to the map. Primary covers all 76 districts on party ballots. General covers the contested races only.
- Party seats: kept as a separate statewide table. No district number, so it does not join.


## DHS SNAP Demographics (June 2025)

Statewide administrative counts by race, age, sex, and citizenship. Use to validate Census S2201 estimates against actual program data. Statewide only — not by district.

- Source: DHS Databook 2025, page 6 (SNAP / formerly Food Stamps)
- PDF: https://humanservices.hawaii.gov/wp-content/uploads/2026/03/DHS-Databook-2025.pdf
- Saved PDF: `data/raw/DHS-Databook-2025.pdf`
- Extracted: `data/processed/dhs_snap_demographics_june2025.json`, `data/processed/dhs_snap_demographics_june2025.csv`

**June 2025 demographic snapshot (percent of SNAP recipients):**

| Characteristic | Category | Percent |
|----------------|----------|---------|
| Sex | Female | 54% |
| Sex | Male | 46% |
| Age | Below 18 | 38% |
| Age | 18–39 | 23% |
| Age | 40–64 | 24% |
| Age | 65 and above | 15% |
| Race/Ethnicity | Hawaiian/part-Hawaiian | 28% |
| Race/Ethnicity | Caucasian | 28% |
| Race/Ethnicity | Other Pacific Islander | 17% |
| Race/Ethnicity | Filipino | 14% |
| Race/Ethnicity | Other Asian | 11% |
| Race/Ethnicity | Black | 2% |
| Race/Ethnicity | American Indian / Alaskan | < 1% |
| Race/Ethnicity | Other / Unknown | < .1% |
| Citizenship | US Citizen | 92% |
| Citizenship | Non-US / Unspecified | 8% |

**SFY 2025 caseload:** average monthly clients 158,516; average monthly cases 83,041; total benefits $694,942,213.

Note: Due to different selection criteria, figures may not match other reports exactly. These are percentages of enrolled recipients, not counts by district.


## BESSD Monthly Summary SFY 2026

Caseload counts by island/branch office. Geographic granularity below statewide, but not at legislative-district level. NPA = Non-Public Assistance = SNAP-only cases.

- Source: BESSD SFY 2026 monthly summary (July 2025–February 2026 available)
- File: `data/raw/SFY-2026-SUMMARY.numbers`
- Extracted: `data/processed/bessd_sfy2026_caseload_by_island.csv`
- Joined to district boundaries on county: `data/boundaries/senate_2022_bessd.geojson`, `data/boundaries/house_2022_bessd.geojson`

**Island/branch codes:** OB = Oahu, HB = Hawaii, KB = Kauai, MB = Maui Branch (Maui + Molokai + Lanai).

**February 2026 persons (latest month with data):**

| Island | SNAP-only (NPA) | Total persons |
|--------|-----------------|---------------|
| Oahu | 82,125 | 94,655 |
| Hawaii | 33,486 | 38,892 |
| Kauai | 7,142 | 7,977 |
| Maui Branch | 15,513 | 17,298 |

Join is on county. Every district in a county receives that county’s island/branch caseload as context. This is not a district-level enrollment count. Original boundary files and the ACS-joined GeoJSON are unchanged.


## Census estimates in the DHS Databook (eligibility proxy, not enrollment)

The Databook reprints American Community Survey (S1701) estimates of the population below poverty thresholds. These are the Census estimates that correspond to program eligibility proxies. They are not administrative enrollment counts.

- Source: DHS Databook 2025, pages 12–13
- Extracted: `data/processed/dhs_databook_census_poverty_estimates.json`, `data/processed/dhs_databook_census_poverty_estimates_2024.csv`

**Important:** The Databook states that for SNAP, a family’s gross income must not exceed **200% FPL** in Hawaii (not the federal 130% threshold).

**Hawaii individuals below percent of poverty (ACS, 2024):**

| Threshold | Persons |
|-----------|---------|
| 50% FPL | 85,760 |
| 125% FPL | 176,587 |
| 150% FPL | 216,581 |
| 185% FPL | 281,418 |
| 200% FPL | 319,667 |

**2024 poverty rate by county:** Honolulu 8.8%, Hawaii 16.7%, Kauai 7.4%, Maui 9.7%.

**2024 children under 18 in poverty:** Honolulu 9.9%, Hawaii 21.2%, Kauai 9.5%, Maui 10.1%.

Compare these Census eligibility proxies to the DHS administrative SNAP snapshot (June 2025: 158,516 average monthly clients) when validating uptake. Geography is statewide or county, not legislative district.


## Statewide SNAP demographics and caseload on district GeoJSON

Statewide DHS SNAP demographics (June 2025) and BESSD SFY 2026 island caseloads are attached to every Senate and House district feature so any front end can display them. Values are statewide or island-level, not district enrollment.

- Files: `data/boundaries/senate_2022_snap.geojson`, `data/boundaries/house_2022_snap.geojson`
- Statewide fields (same on every feature): `dhs_snap_avg_monthly_clients_sfy2025` (158,516), `dhs_snap_avg_monthly_cases_sfy2025` (83,041), sex/age/race/citizenship percents
- Island fields (joined on county): `bessd_snap_only_persons_npa`, `bessd_total_persons` for February 2026
- Note property on each feature states these are not district-level enrollment counts
- Original boundary files and ACS-joined GeoJSON are unchanged

## Mapping Resources

### HAIC guidance
- Know Your District use-case PDF (mentions ESRI/ArcGIS mapping and Living Atlas layers):
  https://haic.hawaii.gov/wp-content/uploads/2026/10/HAIC_Use_Case_Know_Your_District_AI_Agent_2026.pdf

### Official Hawaii maps & ArcGIS tools
- Hawaii Office of Elections – Election Maps: https://elections.hawaii.gov/resources/maps/election-maps/
- City & County of Honolulu Elections App (ArcGIS): https://experience.arcgis.com/experience/7960b9bb3b6543699d364f9001692e81/page/City-and-County-of-Honolulu
- Hawaii Statewide GIS Program: https://planning.hawaii.gov/gis/
- Hawaii State House Districts 2022 (open data): https://opendata.hawaii.gov/dataset/hawaii-state-house-districts-2022
- ArcGIS item (House Districts 2022): https://www.arcgis.com/home/item.html?id=c2f8b485f2064ba1a117ececab301acd
- Office of Elections GIS files: https://elections.hawaii.gov/resources/maps/geographic-information-systems-gis-files/
- Election Precincts 2024 (AdminBnd layer 13): https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/13
- Precinct metadata: https://files.hawaii.gov/dbedt/op/gis/data/precincts.pdf

## Hawaiʻi DHS BESSD / SNAP Participation Reports

### Main pages
- BESSD home: https://humanservices.hawaii.gov/bessd/
- SNAP program page (participation rates & archives): https://humanservices.hawaii.gov/bessd/snap/

### Recent participation / timeliness files (examples)
- SFY 2027 monthly participation (updated monthly): https://humanservices.hawaii.gov/bessd/files/2026/10/SFY-2027-SUMMARY-1.xls
- SFY 2026 participation archive: https://humanservices.hawaii.gov/wp-content/uploads/2026/06/Partic-SFY-2026-WCAG.xlsx
- DHS Databook 2025 (broader program statistics): https://humanservices.hawaii.gov/wp-content/uploads/2026/03/DHS-Databook-2025.pdf

Note: Legislative testimony from BESSD/DHS is typically posted on the Hawaii State Legislature site (capitol.hawaii.gov) under individual bills rather than in a single archive.

## Health Coverage Programs

### Med-QUEST (Hawaii Medicaid)
- Main site: https://medquest.hawaii.gov/
- How to apply: https://medquest.hawaii.gov/en/members-applicants/get-started/how-to-apply.html
- Online application portal: https://medical.mybenefits.hawaii.gov
- Customer service: 1-800-316-8005

### Health Insurance Marketplace
- HealthCare.gov (federal marketplace for Hawaii): https://www.healthcare.gov/
- See plans / estimate financial help: https://www.healthcare.gov/see-plans/

## Housing Assistance Programs

### Section 8 / Housing Choice Voucher (Oahu – HPHA)
- HPHA main site: https://hpha.hawaii.gov/
- Housing Choice Voucher program page: https://hpha.hawaii.gov/programs-and-resources/voucher-programs
- How to apply / waitlist status: https://hpha.hawaii.gov/how-to-apply
- Note: HPHA administers HCV (Section 8) for Oahu only. Neighbor island counties administer their own programs.

### Other housing resources
- HUD Hawaii rental help overview: https://www.hud.gov/states/hawaii/renting
- HHFDC finding affordable housing: https://dbedt.hawaii.gov/hhfdc/looking-for-affordable-housing-in-hawaii/

## Early Childhood / Under-5 Programs

### State coordination
- Executive Office on Early Learning (EOEL): https://earlylearning.hawaii.gov/

### Head Start / Early Head Start providers
- Parents And Children Together (PACT) – Early Head Start & Head Start: https://www.pacthawaii.org/head-start
- Honolulu Community Action Program (HCAP) Head Start: https://www.hcapweb.org/headstart
- Child & Family Service – Early Head Start & Head Start: https://www.childandfamilyservice.org/programs/headstart/
- Maui Economic Opportunity (MEO) Head Start: https://www.meoinc.org/

### Other resources
- The Parent Line – Child Care, Preschool & Play Activities directory: https://www.theparentline.org/resource-directory/child-care-preschool-play-activities/
- Preschool Open Doors (POD) and Child Care Subsidy are administered through DHS (see humanservices.hawaii.gov and earlylearning.hawaii.gov for current eligibility and application details).

## Additional Sources from Build Guide / Use Case PDF

### DOTAX Public Tax Statistics
- Main stats page: https://tax.hawaii.gov/stats/
- Current monthly tax reports: https://tax.hawaii.gov/stats/a5_3txcolrpt/
- Data Dashboard: https://tax.hawaii.gov/data-dashboard/
- Annual reports: https://tax.hawaii.gov/stats/a5_1annual/

### UHERO (University of Hawaiʻi Economic Research Organization)
- Data Portal: https://uhero.hawaii.edu/data/
- Reports & research: https://uhero.hawaii.edu/research/
- Hawaii Housing Factbook 2025: https://uhero.hawaii.edu/the-hawaii-housing-factbook-2025/

### State of Hawaiʻi Data Book (DBEDT / READ)
- Main page: https://dbedt.hawaii.gov/economic/databook/
- 2025 edition: https://dbedt.hawaii.gov/economic/databook/db2025/

### Federal Regional Data
- BLS Hawaii: https://www.bls.gov/regions/west/hawaii.htm
- BEA by place: https://www.bea.gov/data/by-place-us (search for Hawaii)

## S0103 use case — AABD age proxy (Senate only)

Its own query, layer, and data field for AABD.

- File: `data/raw/S0103_senate_districts.json`
- Key column: `S0103_C02_001E` — count of people 65 years and over
- Use: AABD serves people who are elderly (65+) and/or disabled. This is the age side of the eligibility proxy. A Senate district with more residents 65 and over has a larger likely AABD-eligible population on the age criterion.
- Layering: can be shown on its own, or layered with the disability proxy (S1810) for the same Senate district.
- Not for House: Census withholds S0103 for most House districts. A missing House cell is not zero.
- Not enrollment: this is a Census age count, not AABD caseload. Statewide AABD demographics are in the DHS Databook 2025, page 4.
