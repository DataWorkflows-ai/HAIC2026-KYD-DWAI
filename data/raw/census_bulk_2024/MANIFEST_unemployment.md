# Census bulk unemployment tables for HAIC Know Your District

Downloaded Sunday, November 15, 2026, from `www2.census.gov` only (no Census API, no API key, no sign-up).
National ACS table files were streamed, filtered to Hawaii rows, and discarded. Only the Hawaii extracts are kept.
This is an add-on to the earlier ACS 2020–2024 5-year extract in this folder. **The original `MANIFEST.md` was not modified.**

**Box path:** `/workspace/kyd/census_bulk/` (new files only; existing extracts, metadata, and `MANIFEST.md` were left unchanged)

**Workstation path:** `D:\DWAI\HAIC2026-KYD-DWAI-main\HAIC2026-KYD-DWAI\data\raw\census_bulk_2024\`

The D-drive raw folder is add-only. New unemployment extracts, convenience CSVs, this manifest, and the unemployment table-shell extract were added alongside the existing files. Nothing already in the folder was overwritten or deleted.

## License and attribution

Census Bureau API dataset metadata lists the license as [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

These files were obtained as public bulk files from `www2.census.gov`, not through the Census Bureau Data API.

> This product uses Census Bureau data but is not endorsed or certified by the Census Bureau.
>
> https://www.census.gov/data/developers/about/terms-of-service.html

## Hawaii GEO_ID filter

Same prefixes as `MANIFEST.md`. Rows kept when `GEO_ID` starts with:

| Prefix | Geography | Typical count |
|---|---|---:|
| `0400000US15` | State of Hawaii (component 00 only) | 1 |
| `0500000US15` | County | 5 |
| `1400000US15` | Census tract | 461 |
| `1500000US15` | Block group | 1,083 |
| `860Z200US967` | ZCTA 967xx | 77 |
| `860Z200US968` | ZCTA 968xx | 20 |
| `620L900US15` | State House district (2024, SLDL) | 51 |
| `610U900US15` | State Senate district (2024, SLDU) | 25 |

Hawaii ZCTAs were kept with `860Z200US967` and `860Z200US968` only (not the broader `860Z200US96`, which also matches California). Files are pipe-delimited. Estimate columns end in `_E###`; margin-of-error columns end in `_M###`. Decode column codes with `metadata/ACS20245YR_Table_Shells_unemployment.txt` or the official shells already in `metadata/`.

## ACS 2020–2024 5-year table-based summary files (Hawaii rows only)

Source pattern: `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-<table>.dat`

Census source last-modified timestamps on these `.dat` files: 2026-01-29 03:05:15 HST, 2026-01-29 03:05:32 HST, 2026-01-29 03:06:50 HST, 2026-01-29 03:25:48 HST, 2026-01-29 03:25:51 HST, 2026-01-29 03:25:53 HST, 2026-01-29 03:25:55 HST, 2026-01-29 03:25:56 HST, 2026-01-29 03:25:59 HST, 2026-01-29 03:26:03 HST, 2026-01-29 03:26:10 HST, 2026-01-29 03:26:14 HST.

| Table | Title (universe) | HI rows | By geography (state / county / tract / BG / ZCTA 967 / 968 / House / Senate) | Size | SHA-256 | Downloaded (HST) |
|---|---|---:|---|---:|---|---|
| B23025 | Employment Status for the Population 16 Years and Over (Population 16 years and over) | 1,723 | 1 / 5 / 461 / 1083 / 77 / 20 / 51 / 25 | 124.7 KB | `ff0f0c80f236cf8c9eb8f627ec95d43c06d43f25fafeab7d6be23db6f3c8d8a2` | 2026-11-15 20:42:58 HST |
| B23001 | Sex by Age by Employment Status for the Population 16 Years and Over (Population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 672.5 KB | `fe060e2c31fa62f35c07a51245e942b64e538d32d1ae9c3490bcd5ae18940452` | 2026-11-15 20:42:59 HST |
| C23002A | Sex by Age by Employment Status for the Population 16 Years and Over (White Alone) (White alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 120.6 KB | `f0492cd9ff58090905484d5dca2c49d5e5a891df9e0b8a1286a196242add1dfc` | 2026-11-15 20:43:00 HST |
| C23002B | Sex by Age by Employment Status for the Population 16 Years and Over (Black or African American Alone) (Black or African American alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 103.0 KB | `72949fe867236e5312bfdc824dc68d6aa402885ca808743a29a126b7df54b7a5` | 2026-11-15 20:43:01 HST |
| C23002C | Sex by Age by Employment Status for the Population 16 Years and Over (American Indian and Alaska Native Alone) (American Indian and Alaska Native alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 98.5 KB | `1385363ee522122999e7087a1fb2c395feb8d7b4dc9a097cdedde8a441371030` | 2026-11-15 20:43:03 HST |
| C23002D | Sex by Age by Employment Status for the Population 16 Years and Over (Asian Alone) (Asian alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 124.7 KB | `e8ba66e81de5447eb2e2329b8c143459f7006ba022db792ca4e5f0c8f882cf74` | 2026-11-15 20:43:04 HST |
| C23002E | Sex by Age by Employment Status for the Population 16 Years and Over (Native Hawaiian and Other Pacific Islander Alone) (Native Hawaiian and Other Pacific Islander alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 112.7 KB | `1fb59a315aa4f5016d013cbaf2d414d490f727f86732be5963217555f97e8f23` | 2026-11-15 20:43:05 HST |
| C23002F | Sex by Age by Employment Status for the Population 16 Years and Over (Some Other Race Alone) (Some other race alone population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 103.1 KB | `a1b3759d00b808d04cfdfddd2f9c5ec18b314b134f169691f6931b916baaf363` | 2026-11-15 20:43:06 HST |
| C23002G | Sex by Age by Employment Status for the Population 16 Years and Over (Two or More Races) (Two or more races population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 120.6 KB | `b5cb3cdbd9f0d46819039773e5b27c4e0234124d8310d2b3017c3d257c87c2cc` | 2026-11-15 20:43:07 HST |
| C23002H | Sex by Age by Employment Status for the Population 16 Years and Over (White Alone, Not Hispanic or Latino) (White alone, not Hispanic or Latino population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 120.1 KB | `1f0da8a1913e6e2e65581d0f94dd29776ecf36ce2058cde7d92eedd689b2eabe` | 2026-11-15 20:43:08 HST |
| C23002I | Sex by Age by Employment Status for the Population 16 Years and Over (Hispanic or Latino) (Hispanic or Latino population 16 years and over) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 111.6 KB | `02198ab59ab23a595bb3029e14523dfa618ef473f8d313e87d808f32913889e2` | 2026-11-15 20:43:09 HST |
| B23006 | Educational Attainment by Employment Status for the Population 25 to 64 Years (Population 25 to 64 years) | 640 | 1 / 5 / 461 / 0 / 77 / 20 / 51 / 25 | 136.3 KB | `72d188632c06e31cb2ad63a720c741da38923c94a342e214b8f34b7fa6511693` | 2026-11-15 20:43:10 HST |

S2301 (Employment Status subject table) is **not** in the keyless table-based summary files and was not downloaded. The convenience CSVs below rebuild unemployment rates from the B and C tables listed here.

Per-file source URLs and national (unfiltered) row counts:

| Table | Source URL | National data rows streamed | Source bytes | Output file |
|---|---|---:|---:|---|
| B23025 | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b23025.dat | 543,579 | 38.12 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-b23025_Hawaii.dat` |
| B23001 | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b23001.dat | 299,181 | 305.09 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-b23001_Hawaii.dat` |
| C23002A | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002a.dat | 299,181 | 58.62 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002a_Hawaii.dat` |
| C23002B | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002b.dat | 299,181 | 49.70 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002b_Hawaii.dat` |
| C23002C | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002c.dat | 299,181 | 45.61 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002c_Hawaii.dat` |
| C23002D | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002d.dat | 299,181 | 47.78 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002d_Hawaii.dat` |
| C23002E | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002e.dat | 299,181 | 44.42 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002e_Hawaii.dat` |
| C23002F | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002f.dat | 299,181 | 48.62 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002f_Hawaii.dat` |
| C23002G | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002g.dat | 299,181 | 50.73 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002g_Hawaii.dat` |
| C23002H | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002h.dat | 299,181 | 58.20 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002h_Hawaii.dat` |
| C23002I | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c23002i.dat | 299,181 | 51.01 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-c23002i_Hawaii.dat` |
| B23006 | https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b23006.dat | 299,181 | 61.59 MB | `acs_2020_2024_5yr_hi/acsdt5y2024-b23006_Hawaii.dat` |

## Metadata added (new file only)

The official `ACS20245YR_Table_Shells.txt` already in `metadata/` was not modified. A derived extract covering only the unemployment tables was added:

- `metadata/ACS20245YR_Table_Shells_unemployment.txt` — shell rows for the unemployment tables (452 lines + header); SHA-256 `a51bf867e5d9e69fc7786831a31bcb63a024d1bdaab4f6f4e4f0591b983dd703`; size 75.9 KB; written 2026-11-15 20:43:10 HST.

## Convenience files (derived; not Census publications)

Unemployment rate is defined as **unemployed / civilian labor force**. For ages 65 and over in B23001 and C23002*, there is no Armed Forces split, so the published “In labor force” line is used as the denominator (it equals employed + unemployed).

The 90% margin of error of each rate uses the Census approximation for a derived **proportion** (unemployed is a subset of the civilian labor force), from the ACS General Handbook, Chapter 8:

- `MOE(p) = (1 / civilian labor force) * sqrt( MOE(unemployed)^2 − p² * MOE(civilian labor force)^2 )`
- If the term under the square root is negative, the alternative formula is used and `moe_formula` is set to `census_approx_proportion_alt`:
- `MOE(p) = (1 / civilian labor force) * sqrt( MOE(unemployed)^2 + p² * MOE(civilian labor force)^2 )`

Rates are stored as percents (`unemployment_rate_pct`, `unemployment_rate_moe_pct`). When estimates are summed across age, sex, or education lines, the MOE of the sum is `sqrt(sum of component MOE²)`. Those collapsed rows are labeled as deductive aggregations, not published Census lines.

`quality_flag` is `high_moe` when the CV of the rate is at least 30%, the rate MOE is at least as large as the rate, or the rate MOE is at least 5 percentage points; `missing_or_suppressed` when a Census special value or blank was present; `undefined_zero_clf` when the civilian labor force is 0.

Education rates come from B23006 and cover the population **25 to 64 years** only. They are not comparable to the 16-and-over overall rate.

Kalawao County (15005) is included in the county file and noted as a very small population. Headline county comparisons should use Hawaii (15001), Honolulu (15003), Maui (15009), and Kauai (15007).

### State and counties

- **File:** `unemployment_demographics_counties_state.csv`
- **Rows:** 624 (plus header)
- **Size:** 198.6 KB
- **SHA-256:** `d9b39652fde060ee28ca64d5a8911ff9eaae23571dd1364d6f59c1efb41c1875`
- **Written:** 2026-11-15 20:43:10 HST
- **Geographies:** 0400000US15, 0500000US15001, 0500000US15003, 0500000US15005, 0500000US15007, 0500000US15009

### House and Senate districts

- **File:** `unemployment_demographics_house_senate.csv`
- **Rows:** 7,904 (plus header)
- **Size:** 2.75 MB
- **SHA-256:** `0633666a31c3b244febb8544bacdf35a6fd10b9ed4e63a6a200bd18c7a0026dd`
- **Written:** 2026-11-15 20:43:10 HST
- **Geographies:** 76 districts (51 House + 25 Senate)

## Geography coverage and table caveats

- **B23025** publishes all kept levels, including **1,083 block groups** (1,723 Hawaii rows).
- **B23001, B23006, and C23002A–I** publish down to **tract** only, not block group (640 Hawaii rows each: 1 state, 5 counties, 461 tracts, 0 block groups, 77 + 20 ZCTAs, 51 House, 25 Senate).
- At the state, B23025 civilian labor force is 701,694 and unemployed is 34,516. Summing the B23001 age-by-sex civilian labor force lines gives 701,209; unemployed still sums to 34,516. The 485-person (0.07%) denominator difference is in the published tables, not the extract. **Use B23025 for the overall unemployment rate.** Sex, age, race, and education rates necessarily come from B23001, C23002*, and B23006.
- In the House and Senate convenience file, overall rates (B23025) are usable for 74 of 76 districts. Two overall district rows are flagged `high_moe`. Fine-grained cells (race by district, detailed age-by-sex, some education groups) are often `high_moe` because ACS 5-year samples in a single district are small. Prefer the overall, sex, and broader collapsed-age rows, and treat flagged cells as unreliable.

## Totals for this add-on

- ACS Hawaii unemployment extracts: 12 files, 1,995,248 bytes (1.90 MB)
- Convenience CSVs: 2 files
- Metadata added: 1 file
- Manifest: `MANIFEST_unemployment.md`

No national ACS `.dat` files were kept. Existing files in this folder, including `MANIFEST.md`, were not changed.

