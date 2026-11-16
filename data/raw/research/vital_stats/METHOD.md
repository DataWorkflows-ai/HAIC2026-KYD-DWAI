# Hawaii births and deaths by 2022 State House / Senate district — ESTIMATES

**These are modeled estimates, not official counts.** No public source publishes Hawaii births or deaths by legislative district. The Hawaii Department of Health (DOH) has not produced or reviewed these numbers. Label them "estimated" wherever they appear, and cite the sources below.

Built Sunday, Nov 15, 2026 (HST) for the HAIC 2026 Know Your District project.

## Inputs
1. **Hawaii-IBIS (Hawaii Health Data Warehouse, hhdw.org)**, public query system, no login:
   - Live births (`birth/BirthCntyBirth/BirthCount`), by mother's community of residence (24), school complex of residence (40), and county of residence (4), 2000–2024. Residents only. Dataset last updated Jan 5, 2026.
   - All-cause deaths (`mort/MortCnty/Count`, CauseDeathProxy=AllDeaths), by decedent's community, school complex, and county of residence, 2000–2024. Dataset last updated Jan 5, 2026.
   - Queried Sun Nov 15, 2026, 23:23 HST. The raw result pages are in `ibis_raw/`. The counts were extracted unchanged into `ibis_*_counts_by_*.csv`.
2. **HHDW 2024 Geography Documentation** (`Geography-Documentation-3.04.24.pdf`). For vital statistics, IBIS codes island, community and school complex from the residence **ZIP code**. County and PCSA are coded from census tract. The ZIP → community / school complex table (141 ZIPs) was parsed into `hhdw_vital_zip_to_community_schoolcomplex.csv`.
3. **2020 Census DHC** (`hi2020.dhc.zip`, geo header): 14,732 populated blocks (total population 1,455,271), each with its ZCTA5, county, and internal point.
4. **2022 State House (51) and Senate (25) district polygons** from geoportal.hawaii.gov (the `gis_districts` folder downloaded earlier).
5. **DBEDT State of Hawaii Data Book 2025, Section 2** (`DB2025_section02.xlsx`): Table 2.01 (state resident births and deaths, 2000–2024), Table 2.05 (resident births by county, 2021–2024), Table 2.17 (resident deaths by county, 2021–2024). Used only for reconciliation.

## Method (population-weighted areal allocation)
1. Each 2020 block is assigned to an IBIS community and school complex through its ZCTA, using the HHDW ZIP table. Only ZCTA `99999` (153 people) had no match, and it is left unallocated.
2. Each block is assigned to a 2022 House and Senate district by testing its Census internal point against the 2022 GIS polygons. 868 blocks with 322 people fell just outside every polygon (coastline slivers) and were assigned to the nearest polygon.
   - The district codes embedded in the DHC do **not** match the 2022 GIS layers for about half the blocks. Those codes appear to be a different plan vintage, so they were not used.
3. Share(unit → district) = 2020 population of the unit that falls inside the district, divided by the unit's total 2020 population. The shares are in `crosswalk_ibis_community_schoolcomplex_to_2022_house_senate.csv`. The block-level audit is in `crosswalk_blocks_2020_to_zip_community_district.csv`.
4. District estimate for each year = Σ over units of (IBIS count × share). Every year uses the same 2020 population weights.
5. **Primary files** use the 24 communities:
   - `vital_stats_births_deaths_by_house_district_ESTIMATE.csv`
   - `vital_stats_births_deaths_by_senate_district_ESTIMATE.csv`
6. **Sensitivity files** use the 40 school complexes (`*_via_school_complex_ESTIMATE.csv`). For 2024, the median district differs from the primary estimate by:
   - House: 1.7% for births and 2.5% for deaths, with a maximum of about 39%.
   - Senate: 0.5% for births and 1.0% for deaths, with a maximum of about 23%.
   - A large gap means the district sits across unit boundaries, and its estimate is less certain.

## Suppression rules
- IBIS follows the National Center for Health Statistics (NCHS) rule that **counts below 9 are suppressed**, and rates based on 19 or fewer counts are suppressed. IBIS also labels estimates by relative standard error (RSE): Stable, Unstable (RSE 30–49.9%), or Very Unstable (RSE 50% or more).
- In the IBIS result data, a suppressed cell is returned as `MeasureValue 0` with the attribute `Suppressed`. The extracted CSVs keep IBIS's value and the `Suppressed` marker exactly as returned. **A 0 marked Suppressed is not a real zero.**
- **Suppressed cells are not allocated.** `share_suppressed_flag` lists how many suppressed cells touched a district and what share of the district's 2020 population they cover. `share_suppressed_births` and `share_suppressed_deaths` give the same share as a fraction.
- Where suppressed cells occur:
  - Community deaths: 7 cells, all Lanai in early years. There are no suppressed community births.
  - School-complex files: "No School Complex - Military" (births and deaths) and Lanai (deaths).
- Small district values are themselves unstable. Do not publish single-year district estimates below about 20 without a caveat. Pooling several years (for example, 2020–2024) is better.

## Reconciliation (full table in `RECONCILIATION.csv`)
- The allocation conserves totals. For every county and year, the district sum equals the sum of the IBIS community counts, to within 0.1 from rounding.
- **IBIS community sum compared with IBIS county totals:**
  - Births: between −2.5% and +1.0% across all counties and years (2020–2024: within ±0.7%).
  - Deaths: between −2.65% and +1.1% (worst case Maui 2016).
  - IBIS explains this: community comes from ZIP and county comes from census tract, and some records are missing one field or the other.
- **Compared with DBEDT/DOH totals:**
  - Births, 2024: state 14,857 estimated vs 14,883 DBEDT (−0.2%). By county, the differences are between −0.3% and +0.6%.
  - Deaths, 2024: state 12,373 vs 12,489 (−0.9%). By county, the differences are between −1.3% and −0.7%.
  - Deaths, 2020: state −2.2%.
  - Maximum gap against DBEDT for any county or year, 2021–2024: 2.8% (Maui deaths, 2021).
  - DBEDT Maui County includes Kalawao.

## Caveats
- These are estimates. The method assumes births and deaths are spread across a community in proportion to its **total** 2020 population. It does not use age structure. That assumption overstates deaths in young or military-heavy districts and understates them in older ones. Births are affected the same way by the share of women of childbearing age.
- 2020 population weights are applied to every year from 2000 to 2024. Early years carry more error, because population has shifted since then. This includes Maui after the 2023 wildfires.
- ZCTAs only approximate postal ZIP codes. PO-box ZIPs have no ZCTA, but they map to the same communities, so community totals are not affected.
- Counts are by place of residence and Hawaii residents only. Deaths of residents that occur out of state are excluded.
- Districts are the 2022 plans in the geoportal layers. ACS figures for "2024 SLD" may use a different district vintage.

## Citation and terms
- **Hawaii-IBIS:** Hawaii State Department of Health, Hawaii Health Data Warehouse, Office of Health Status Monitoring, Birth Data / Death Data. Live Births Count and Mortality Count, 2000–2024. Dataset last updated Jan 5, 2026. Accessed Nov 15, 2026. https://hhdw.org/report/
  - Under the IBIS query-system data use agreement, the data may be used **for statistical reporting and analysis only**. Users must not try to identify or contact individuals, or link the data in a way that could identify anyone. Data may be reused with this citation.
- **DBEDT:** State of Hawaii Data Book 2025, Section 2, Tables 2.01, 2.05 and 2.17. Source: Hawaii State Department of Health, Office of Health Status Monitoring.
- **U.S. Census Bureau:** 2020 Census Demographic and Housing Characteristics File (public domain).
- **District boundaries:** Hawaii Statewide GIS Program (public domain; State of Hawaii terms of use).
