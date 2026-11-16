# HPD Annual Report crime tables — extraction notes

Extracted once on 2026-11-15 (HST) from the Honolulu Police Department annual reports. The full PDFs were
downloaded to /tmp only and deleted after extraction (Mitchell approved). Only small text snippets of the statistics
pages are kept, in `evidence/`.

Hub page: https://www.honolulupd.org/information/annual-report/ (lists 2021–2025). The 2017–2020 reports are still hosted under
honolulupd.org/wp-content/uploads/2020/… and /2021/… and were found through the Wayback CDX index. 2015–2016 PDFs exist but contain no
extractable beat/district text, so they were skipped. 2009–2014 reports also exist and were not used.

| Report | PDF URL | Table 1 page (PDF) | District/Beat table pages (PDF) | Beat-map pages (PDF) |
|---|---|---|---|---|
| 2017 | https://www.honolulupd.org/wp-content/uploads/2020/09/HPD2017annualreport-1.pdf | 19 | 21–28 (single year) | none |
| 2018 | https://www.honolulupd.org/wp-content/uploads/2020/09/HPD2018annualreport.pdf | 28 | 33–40 (cols 2017, 2018) | none |
| 2019 | https://www.honolulupd.org/wp-content/uploads/2020/10/HPD2019annualreport.pdf | 24 | 30,32,…,44 | 31,33,…,45 |
| 2020 | https://www.honolulupd.org/wp-content/uploads/2021/06/HPD_-ANNUAL-REPORT_2020_FINAL_low-res.pdf | 28 | 34,36,…,48 | 35,37,…,49 |
| 2021 | https://www.honolulupd.org/wp-content/uploads/2022/05/HPD_-ANNUAL-REPORT_2021_FINAL.pdf | 32 | 38,40,…,52 | 39,41,…,53 |
| 2022 | https://www.honolulupd.org/wp-content/uploads/2023/05/HPD2022annualreport.pdf | 30 | 34,36,…,48 | 35,37,…,49 |
| 2023 | https://www.honolulupd.org/wp-content/uploads/2024/05/HPD_-AR_2023_FINAL_PDF-A_REDUCED.pdf | 36 | 38,40,…,52 | 39,41,…,53 |
| 2024 | https://www.honolulupd.org/wp-content/uploads/2025/05/HPD_-AR_2024_WEB_Archive.pdf | 28 | 30,32,…,44 | 31,33,…,45 |
| 2025 | https://www.honolulupd.org/wp-content/uploads/2026/05/HPD-Annual-Report-2025.pdf | 32 | 34,36,…,48 | 35,37,…,49 |

The PDFs' sha256 values are in MANIFEST.md.

## Method
`pdftotext -layout` was run on each PDF. `scripts/extract_hpd.py` parses Table 1 (Crime Index) and every page that has a BEAT header and a TOTAL row.
Each beat row has 8 columns (murder, rape, robbery, aggravated assault, burglary, larceny, auto theft, total) × 1 or 2 years.
Year order comes from the column header: the 2018 report is ordered prior→current, and 2019+ reports are ordered current→prior. Districts are taken
from the "DISTRICT n" page heading and cross-checked against the beat's first digit, with 0 mismatches.
`scripts/build_outputs.py` writes the CSVs and the JSON and runs QA.

## Outputs
- `hpd_index_citywide_by_year.csv`: Table 1 for every vintage. Each report repeats 5 years, so values are tagged with `report_year`, `is_own_year_report` and `is_latest_vintage`. Coverage is 2013–2025.
- `hpd_offenses_by_district_by_year.csv`: the TOTAL row of each district table, long format, covering 7 offenses plus violent_total, property_total and total.
- `hpd_offenses_by_beat_by_year.csv`: 158 beats × 2017–2025, long format. Prior-year columns are kept with `is_own_year_report=False`.
- `hpd_beat_wide_own_year_report.csv`: a wide convenience table with one row per beat-year, taken from that year's own report.
- `hpd_crime_annual_reports.json`: combined data plus the page map.
- `QA_beat_vs_district.csv` and `QA_district_sum_vs_citywide.csv`.

**Use `is_own_year_report=True` for analysis.**

## QA results
1. **Sum of beats = district TOTAL row:** 0 differences across all 9 reports, all districts and all offenses.
2. **Row arithmetic (7 offenses = printed total):** this passes everywhere except one source error. In the 2021 report's *prior-year (2020)* column for District 1, the robbery figures don't add up to the printed totals in 20 beats, a 66-offense gap at district level. The 2020 report's own 2020 column is internally consistent and equals the printed totals, so use that one.
3. **Restatements between vintages (own report vs next year's prior column):** all beat totals are identical. The only offense-level difference is the 2020 D1 robbery case above.
4. **District sums vs Table 1 citywide:** these do **not** match, and that is by design, not a parse error. The sum of the 8 districts is higher than Table 1 by +7% to +17% in total offenses (2025: 17,594 vs 15,096, +16.6%). The gap is mostly larceny (+11–25%) and forcible rape (+23–62%). Motor vehicle theft and aggravated assault are slightly *lower* in district tables. Table 1 is the FBI UCR Summary (SRS) count, converted from NIBRS and with the hierarchy rule applied. The District/Beat tables come straight from HPD's Case Report System (CRS) as offense counts. Murder in Table 1 comes from Homicide Detail. Use Table 1 for official citywide figures, and use district/beat tables for geographic *distribution*.
5. **Table 1 revisions:** Table 1 was revised starting with the 2023 report. For example, 2021 violent crime is 2,516 in the 2021/2022 reports and 2,247 in the 2023–2025 reports, and 2021 larceny is 20,079 vs 19,092. These values were restated after the NIBRS→SRS conversion. `is_latest_vintage=True` gives the newest restatement.

## NIBRS → SRS
From 2018 on, HPD's text says count data was "obtained from the Case Report System (CRS) and converted from NIBRS to the Summary Reporting System"; the 2022+ reports say this explicitly. The index offenses use FBI SRS definitions, and "forcible rape" uses the revised penetration-based definition. The 2025 report's burglary breakdown adds "Unknown Time" categories (NIBRS requirement). Murder comes from Homicide Detail. Because of this, don't mix these counts with the AG's NIBRS-based dashboard (crimestats.hawaii.gov).

## Table-format changes
- **2017:** one year per table, with all 8 districts on consecutive pages and no maps.
- **2018:** two years, ordered prior then current, and no maps.
- **2019–2025:** two years, ordered current then prior, with each beat table followed by a beat-map page.
- **Table 1 coverage:** the 2017 report covers 2013–2017, and later reports cover a rolling 5 years.
- **District names:** these changed slightly. For example, District 8 is "Makaha/Waianae/Kapolei" in 2021 and "Waianae (Kapolei/Waianae/Makaha)" in 2022+, and Hawaiian diacritics were added in 2024+.
- **Beat set:** the same 158 beats appear every year 2017–2025 (D1 24, D2 13, D3 17, D4 22, D5 23, D6 13, D7 26, D8 20). There was no renumbering. This matches HPD policy "Patrol Command Boundaries": 24+23+13+26+13+17+22+20 = 158 motor beats.
