# DBEDT relevance review for HAIC 2026 Know Your District

This review classifies the unique DBEDT/READ files saved in `data/raw/dbedt.hawaii.gov/economic/` for the HAIC 2026 resident-profile use case. It does not delete or move any raw files.

## Challenge data needs extracted from the rules

Resident profiles need source-cited, year-tagged, geography-tagged measures covering:

- population totals and age groups
- households and household situations
- income, earnings, poverty, and financial stress
- employment status, unemployment, jobs, occupations, wages, and industries
- housing inventory, tenure, housing costs, affordability, overcrowding, and housing demand
- education, language, race/ethnicity, disability, veterans, commuting/place of work, and health-insurance/SNAP-style indicators where available
- county and state comparisons for each district estimate
- program eligibility and uptake context from public sources (not covered well by this DBEDT file set)

Geographies that can support district profiles or crosswalk/apportionment include: legislative district, census tract, block group, ZIP/ZCTA, county, CDP/place, county subdivision/CCD, PUMA, island, and state benchmarks. The best geography in this DBEDT subset is census tract; most other DBEDT files are county/state context.

## Tier counts

| Relevance | Files |
|---|---:|
| HIGH | 17 |
| MEDIUM | 166 |
| LOW | 729 |
| **Total** | **912** |

## HIGH files grouped by topic

### Employment and unemployment at census-tract level

- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2010.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2010.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2011.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2011.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2012.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2012.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2013.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2013.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2014.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2014.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2015.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2015.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2016.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2016.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2017.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2017.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2018.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2018.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2019.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Older than the 2020s tract series, so use for trend/history rather than current profile figures. Years: 2019.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2020.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2020.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2021.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2021.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2022.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2022.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2023.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2023.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2024.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2024.
- `data/raw/dbedt.hawaii.gov/economic/labor/LFR_LAUS_CensusTract-2025.xls` — Census-tract labor-force, employed, unemployed, and unemployment-rate data can be crosswalked/apportioned to House and Senate districts. Years: 2025.

### Older adults, poverty, and housing

- `data/raw/dbedt.hawaii.gov/economic/reports-archive/Elderly_Population_in_Hawaii-Housing_with_Appendix_on_Kau_district_Dec2021.pdf` — Directly relevant older-adult housing and poverty report with a sub-county district appendix; useful as a district-profile exemplar and methods reference. Years: 2021.

## Notable gaps in the downloaded DBEDT set

- No official House/Senate district boundary files or tract/block/ZIP-to-legislative-district crosswalks are present in the DBEDT subset.
- No DBEDT file provides complete legislative-district resident profiles for all 51 House and 25 Senate districts; the Census ACS files elsewhere in `data/raw/census.hawaii.gov/acs/` are stronger for House/Senate tables.
- Most DBEDT demographic, income, housing, labor, and industry data is county/state level, so it is best used as benchmark/context rather than direct district estimates.
- No block-group-level DBEDT data was downloaded; block groups would be useful for more accurate apportionment inside districts.
- No DBEDT ZIP/ZCTA- or CDP-level resident-profile dataset was found in the downloaded DBEDT rows.
- Program eligibility and uptake data is not represented in the DBEDT download and will need a separate public-source inventory.
- Several useful DBEDT demographic/language supplemental files were skipped by the size policy and should be considered for targeted fetches if the repo owner wants a tighter curated DBEDT set.

## Skipped DBEDT links worth a targeted pull

These were not fetched in this pass; they look higher-value than typical skipped tourism/energy/background files:

- https://files.hawaii.gov/dbedt/economic/archive/reports/Historical-Statistics-of-Hawaii.pdf — Broad DBEDT reference useful for validation and historical context. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/library/facts/Facts_Figures_browsable.pdf — Broad DBEDT reference useful for validation and historical context. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/library/facts/Facts_Figures_printable.pdf — Broad DBEDT reference useful for validation and historical context. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Brain_Drain_Hawaii_Born_Population.pdf — Potentially useful demographic/social/economic reference or tabular supplement. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Detailed-race-characteristics_supplemental-tables.xlsx — Supplemental tabular data for a downloaded race-characteristics report; likely more usable than the PDF alone. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/SelectedRacesCharacteristics_HawaiiReport.pdf — Potentially useful demographic/social/economic reference or tabular supplement. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Non_English_Speaking_Population_in_Hawaii_April_2016.pdf — Language data aligns with resident-profile language/access needs. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Detailed_Language_March2016.pdf — Language data aligns with resident-profile language/access needs. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Commuter adjusted population in Hawaii_May2024.pdf — Commuting/daytime population can help explain district daytime vs resident populations. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.
- https://files.hawaii.gov/dbedt/economic/archive/reports/Daytime_Population_Dec19_2014.pdf — Commuting/daytime population can help explain district daytime vs resident populations. Reason recorded: Skipped by priority policy after a full DBEDT crawl exceeded the 2 GB guidance.

## Notes on older and superseded files

- Older census-tract unemployment spreadsheets remain HIGH because tract data can be crosswalked to districts, but use the latest available tract year for current profiles and older years only for trend/history.
- Older monthly county economic-condition PDFs are LOW because the latest downloaded profile for each county/state supersedes them for benchmark use.
- Older QCEW/CES/OEWS labor releases and archived input-output files are mostly LOW when newer downloaded releases cover the same measure.
- Tourism, energy, visitor, foreign-student, meeting-notice, and most tax-credit files are LOW for this resident-profile challenge.

## CSV details

See `data/DBEDT_RELEVANCE.csv` for one row per unique DBEDT local path with `relevance`, `topics`, `geography_level`, `years_covered`, and `rationale`.
