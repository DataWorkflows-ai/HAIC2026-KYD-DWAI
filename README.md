# Know Your District (HAIC 2026, Challenge 1)

**Live app:** https://know-your-district-zio4.onrender.com — no login, no setup. Shareable links work, e.g. https://know-your-district-zio4.onrender.com/#/HD-44/map
(The free host sleeps when idle; the first load after a quiet spell can take 30–60 seconds.)

A nonpartisan, cited profile of every Hawaiʻi State House and Senate district (2022 plan) for legislators and staff:
who lives there, how they are doing, which assistance programs fit, and where people who look eligible are not being reached.
Every number on screen traces to a named source, vintage and method, with margins of error where the source publishes them.

## Try it in two minutes

1. **Overview** — pick a district next to its name: headline figures with county and state comparisons, all indicators with Print and CSV, top program matches, peer districts.
2. **Map** — pick any indicator ("Most used" first). Each district shows its number and value; hover for the value and rank; picking a district anywhere flies the map to it.
3. **Compare** — any two districts (or a district and the state), with the Census significance test on every row.
4. **Rankings** — all 51 House or 25 Senate districts on poverty, SNAP gap, unemployment, LIDAC share and violent crime (Oʻahu), sortable, printable, CSV.
5. **Programs** — 15 programs scored for fit, cross-program eligibility estimates (school meals, Lifeline, LIHEAP, WIC, Med-QUEST), unemployment by group, test scores, school meals, HUD housing, crime (Oʻahu, estimate), island Med-QUEST/TANF/SNAP context.
6. **Ask** — plain-English questions ("Which programs fit HD 44?", "Compare SD 12 with the state", "Unemployment by age in HD 5"). Answers only use figures returned by tools and cite each one.
7. **Sources** — a 27-source library (also in [SOURCES.md](SOURCES.md)) and the build-time verification report (344 checks pass, 0 fail).

## What the data covers

- **Census ACS 2020–2024** district profiles (DP02–DP05, S1701 poverty ladder, S2201 SNAP, unemployment by sex/age/race/education)
- **SNAP gap**: people below 200% of poverty (Hawaiʻi's SNAP limit) not in SNAP households, by district (estimate)
- **2025 unemployment** (DBEDT/LAUS, tract estimates rolled to districts; county trend 2014–2025)
- **Low-income and disadvantaged communities (LIDAC 2026)** share of residents
- **HUD subsidized housing** (2025), **free/reduced school meals** (SY2025-26) and **2025 Smarter Balanced / HSA Science** results (by school location; charter schools excluded)
- **HPD crime 2017–2025** for Oʻahu (estimate; beat lines traced from report maps)
- Island-level **Med-QUEST, TANF and SNAP** caseloads from the DHS Databook and BESSD

Estimates are labelled as estimates on screen, with the method and caveats beside them.

## How it works (and why it is safe to put in front of the public)

- **Two tiers.** The numbers tier is plain code over a precomputed, read-only fact table — no AI writes or alters a number.
  The language tier only chooses which tool to call and with what arguments; it never writes SQL, and any number in its reply
  that cannot be traced to a tool result is removed before the answer is shown.
- **Read-only by design.** The public deployment opens the bundled SQLite database read-only; the Postgres mode uses a
  SELECT-only role. Every data and agent request is written to a hash-chained, append-only audit log
  (a local file here, a Postgres table in live mode), so tampering is detectable.
- **Population-level only.** No individual records, no address lookup; questions about individuals and partisan/electoral advice are refused.
- **Verified at build time.** Hand-entered report figures are re-checked against their PDFs and workbooks, Census variables against published totals,
  and independent sources against each other (`python kyd/verify/run.py`).

Architecture details: [kyd/ARCHITECTURE.md](kyd/ARCHITECTURE.md).

## Run it locally

```bash
pip install -r kyd/backend/requirements.txt
cd kyd/backend && uvicorn app.main:app --port 8060     # open http://localhost:8060
cd kyd/backend && python -m pytest -q ../tests           # tests
```
The database (`kyd/data/kyd.sqlite`) and the built frontend (`kyd/frontend/dist`) are committed, so no build step is needed.
Rebuild the data with `python kyd/etl/load_acs_profile.py` (chains every loader). Deploy: `render.yaml` (Render Blueprint).

## Additional features / roadmap

Designed and scoped, not in this release:

- **County council districts** as a third district type, with boundaries and labels on the map
- **Customizable indicator table**: show/hide, reorder and "add indicator", remembered per browser
- **Finder**: search by district, legislator, neighborhood or ZIP (the place/ZIP lookup already powers the agent)
- **Map over ranked table** (one indicator drives both; click either to highlight the other)
- **Program uptake-gap finder**: districts with similar need but lower program use, from the Neo4j program/population graph
- **Postgres (Neon) deployment** with the audit log and per-user activity history; local-model option for offices that cannot send data off-site
- Chat docked beside the profile; WIC clinic locations; births and deaths by district (estimate files prepared)

---

# Data and program notes

## What a legislator can query

This is the core of the app. Five programs, each its own capability. Filters are the controls inside each one. Any front end calls `list_programs()` and renders the result.

```python
from scripts.programs import list_programs
list_programs()
```

| Program | What it answers | Filters |
|---------|-----------------|---------|
| **SNAP** | Who is enrolled vs who looks eligible, by district. The only program with a district gap. | SNAP household count, people below 200% FPL, gap, person-level estimate |
| **TANF / TAONF** | Where families with children in poverty are concentrated. | Related children under 18 below poverty, island caseload vs county poverty, race under-enrollment |
| **General Assistance** | Where temporarily disabled working-age adults may be eligible. | Disability rate, adults 18-64 below poverty, working-age share. One, two, or all three. |
| **AABD** | Where aged, blind, or disabled residents may be eligible. | Disability prevalence, 65+ (Senate only), foreign-born / Oceania / year of entry |
| **Med-QUEST** | Island enrollment, where the uninsured are, and where income-eligible people are concentrated. | Enrollment by island (2015-2025), uninsured rate by district, poverty at 125/150/185/200% FPL, enrollment-to-need ratio by island (lower = thinner enrollment relative to poverty; higher does not mean more eligible) |


**How TANF, GA, AABD, and Med-QUEST work.** These four programs characterize who is enrolled using DHS statewide demographic snapshots. They characterize where need is concentrated using Census district-level poverty, disability, age, and insurance data. They compare the statewide enrolled profile to the district-level need profile. They do not directly measure the eligible-but-not-enrolled gap at the district level. SNAP is the exception: it has district-level enrollment and a district gap. This explanation is in `list_programs()` as `method_for_tanf_ga_aabd_medquest.ui_text` so a front end can show it on screen.

Except for SNAP, these are eligibility proxies. They are not district enrollment and not a district gap. Each program is separate. A user can open one, or layer several.

## District boundaries

The map uses official 2022 House and Senate polygons from the Hawaiʻi Statewide GIS Program AdminBnd MapServer. One service holds both chambers. Source: Hawaii State Office of Elections, March 2022. The files are saved in the repo and are not downloaded when the app runs.

- Service: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer
- Senate GeoJSON (layer 34): https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/34/query?where=1%3D1&outFields=*&f=geojson
- House GeoJSON (layer 33): https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/33/query?where=1%3D1&outFields=*&f=geojson
- Saved as `data/boundaries/senate_2022.geojson` and `data/boundaries/house_2022.geojson`

**Senate, 25 polygons.** Attributes: `county`, `senate_id` (1–25), `senate_name`, `senate_abbr`, and short code `state_senate` (S01–S25).

**House, 51 polygons.** Attributes: `county`, `house_id` (1–51), district code `state_house` (H01–H51), `house_abbr`, and `house_name`.

Join key to the ACS tables is chamber plus `senate_id` or `house_id`. One feature per district; multipart islands are not separate districts. Full field notes are in `data_sources.md` and `data/boundaries/README.md`.

**Election precincts, 250 polygons.** AdminBnd layer 13, Office of Elections, May 2024. Each precinct carries its 2022 House code (`state_hous`, H01–H51) and Senate code (`state_sena`, S01–S25), plus county. That is the crosswalk for rolling precinct election results up to a legislative district. It does not include total population, target population, or deviation from target.

- Layer: https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/13
- Metadata: https://files.hawaii.gov/dbedt/op/gis/data/precincts.pdf

## 2022 election results

Use case: how a district voted in 2022. Join to the map on district number. Full notes are in `data_sources.md`.

- Primary, August 13, 2022: `data/processed/election_2022_primary_by_district.csv`. All 25 Senate and 51 House districts. Party-ballot totals, not one combined district vote.
- General, November 8, 2022, final: `data/processed/election_2022_general_by_district.csv`. One row per contest, district, and candidate. 21 Senate and 42 House contests. Missing contests were not printed, usually because they were uncontested.

## ACS 2020–2024 profiles

The repo has both ACS 2020–2024 5-year workbooks: `data/raw/acs2024_5yr_house_hi.xlsx` and `data/raw/acs2024_5yr_senate_hi.xlsx`. Each has DP02, DP03, DP04, and DP05.

- DP02 (House and Senate): households, education, language, veterans, disability, internet.
- DP05 (House and Senate): age and sex, race and ethnicity, housing units, citizen voting-age population.
- Subject tables are separate. S1801 disability by type and S2201 SNAP receipt cover House and Senate. S0103 (age 65+) is Senate only; House is withheld for most districts. S1701 poverty detail is not available at House or Senate district level.

Every number is a sample estimate. Show the margin of error, the table ID, and the 2020–2024 vintage. Hawaii districts are drawn on permanent residents and range from about 24,000 to 84,000 people, so compare percents, not raw counts. These district numbers are the 2022 districts. Do not compare them with pre-2022 ACS or 2020 Census redistricting tables.

## Verify against the original source data

These steps check the committed district figures against the official DBEDT ACS 2020–2024 five-year workbooks. Run them from the repository root.

The Excel files are required for the source-verification tests. They are not required to run the app. The app uses the committed `data/districts.db`.

Install the Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create `data/raw` and download the official DBEDT workbooks. Keep the filenames exactly as shown:

```bash
mkdir -p data/raw
curl -L -o data/raw/acs2024_5yr_house_hi.xlsx "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_house_hi.xlsx"
curl -L -o data/raw/acs2024_5yr_senate_hi.xlsx "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_senate_hi.xlsx"
```

Run the tests:

```bash
python3 scripts/test_comparison.py
python3 scripts/test_defects.py
```

`test_comparison.py` checks ranking, chamber separation, missing values, and CSV contents against the committed data. `test_defects.py` reads the two Excel files and checks that the committed rent-burden figures match the GRAPI section of the source workbooks for all 76 districts. Do not run `scripts/process_acs.py` or `scripts/load_sqlite.py` as part of this check; those rewrite the committed tables.

## SNAP gap analysis (additive)

S2201 (SNAP receipt) and S1701 (poverty / income-to-poverty) JSON tables for House and Senate districts are now in `data/raw/`. These support the district-level enrolled-vs-eligible gap analysis described in `SNAP_Analytical_Framework.md`.

- `data/raw/S2201_senate_districts.json`, `data/raw/S2201_house_districts.json` — enrolled demographic profile
- `data/raw/S1701_senate_districts.json`, `data/raw/S1701_house_districts.json` — income-eligible population proxy (<130% FPL)

The front-end-agnostic interface is `scripts/snap_gap.py` (`get_snap_gap(chamber, district_number) -> dict`). Any front end can call it. Map configuration, boundary GeoJSON, and existing app code are unchanged.

## TANF/TAONF eligibility proxy (unique feature)

This is a distinct, searchable query for identifying need by district. It is not a SNAP measure and not an enrollment count.

**What it answers:** How many related children under 18 live below the poverty level in this district? That is the best public approximation of families with related children who may be income-eligible for TANF/TAONF.

**Source:** ACS S1701 `C02_005E` — below poverty level, related children of householder under 18 years. Counts only. The percent column is not used in the calculation.

**How to query it:**

```python
from scripts.tanf_proxy import get_tanf_proxy, search_tanf_proxy

# One district
get_tanf_proxy("senate", 1)

# All districts, ranked by count
search_tanf_proxy()

# House only, districts with at least 500 related children below poverty
search_tanf_proxy(chamber="house", min_count=500)
```

Each result is a plain dict: count, margin of error, total related children, percent of related children below poverty, and caveats. Any front end can render it. No UI framework is imported.

**Why it is separate:** SNAP can be compared enrolled-vs-eligible at district level. TANF/TAONF cannot — DHS publishes demographics statewide only. This query fills that gap with a district-level need signal so a user can see where families with children in poverty are concentrated, then compare that pattern to the statewide enrolled profile.

## TANF by island (standalone)

Its own capability. Not nested under SNAP. Call `get_tanf_by_island()` and show the result as its own card or section.

It summarizes BESSD TANF caseload by island, computes enrollment per 1,000 residents, and sets that next to the county poverty rate from Census S1701.

```python
from scripts.tanf_by_island import get_tanf_by_island
get_tanf_by_island()  # February 2026 by default
```

February 2026:

| Island | TANF persons | Per 1,000 residents | County poverty rate |
|--------|--------------|---------------------|---------------------|
| Hawaii | 1,443 | 6.87 | 16.7% |
| Maui | 424 | 2.64 | 9.7% |
| Kauai | 188 | 2.56 | 7.4% |
| Oahu | 2,326 | 2.35 | 8.8% |

Hawaii County is highest on both per-capita TANF and poverty rate. These are island/county figures, not district enrollment.

## TANF under-enrollment by race (standalone metric)

Its own metric. Compares the statewide DHS TANF race profile to the district poverty profile from Census S1701.

```
under_enrollment_pp = district share of people below poverty
                    − statewide share of TANF recipients
```

Positive means the group is a larger share of the district's poverty population than of statewide TANF recipients: under-enrollment relative to need.

```python
from scripts.tanf_underenrollment import get_tanf_underenrollment
get_tanf_underenrollment("senate", 1)
```

Example: if Native Hawaiians are 33% of statewide TANF recipients but 40% of a district's poverty population, under-enrollment is +7 percentage points.

This is an indirect comparison. DHS demographics are statewide, not by district. DHS and Census race categories do not match exactly (Hawaiian/part-Hawaiian vs Native Hawaiian / Pacific Islander). The result includes both the combined NHPI comparison and the 33% Hawaiian-only comparison. Show it as its own card.

## General Assistance (standalone)

Reported separately from SNAP, TANF, AABD, and Med-QUEST. Three lenses. The user can turn on one, two, or all three.

| Lens | What it shows | Source |
|------|---------------|--------|
| disability | Percent with a disability | S1810 |
| poverty_18_64 | Adults 18-64 below poverty | S1701 C02_006E |
| age_structure | Working-age share (18-64) | DP05 |

A higher disability rate, more adults 18-64 in poverty, or a larger working-age share means a larger likely GA-eligible population.

```python
from scripts.ga_proxy import get_ga_proxy

get_ga_proxy("senate", 1)                                          # all three
get_ga_proxy("senate", 1, lenses=["disability"])                   # one
get_ga_proxy("senate", 1, lenses=["disability", "poverty_18_64"])  # two
```

Statewide snapshot from DHS Databook 2025, page 5: 4,432 average monthly clients. 59% male, 41% female. 69% are 40-64. Show as its own card.

## AABD (standalone)

Aid to the Aged, Blind, and Disabled. Its own card, separate from other programs.

Disability prevalence from S1810 is its own filter. Foreign-born from DP02 is its own filter: total foreign-born, Oceania (Pacific), and year of entry (2010 or later / before 2010). Districts with a higher Pacific Island foreign-born population may have more AABD-eligible residents. A higher rate means more people who may meet the disability criterion. The 65+ count from S0103 is a separate Senate-only age filter.

```python
from scripts.aabd import get_aabd
get_aabd("senate", 1, filters=["disability"])   # disability only
get_aabd("senate", 1)                           # disability and 65+
```

Statewide snapshot from DHS Databook 2025, page 4: 754 average monthly clients. 65% female. 72% are 65-79. 51% Other Pacific Islander. Not district enrollment and not a gap.

## Med-QUEST (standalone)

Its own card, separate from other programs. Enrollment by island from DHS Databook 2025, page 27. SFY 2015-2025.

```python
from scripts.medquest import get_medquest, get_medquest_trend
get_medquest(2025)                    # all islands, latest year
get_medquest(2025, island="oahu")     # one island
get_medquest_trend("statewide")       # 2015-2025 series
```

SFY 2025: 404,922 statewide. Oahu 244,167 (60.3%), Hawaii 85,322 (21.1%), Maui 47,691 (11.8%), Kauai 22,964 (5.7%), Molokai 3,881, Lanai 897.

Island enrollment only. Not by legislative district. Not a gap.

Unique filter: uninsured rate by district from Census S2701. A higher uninsured rate may mean more Med-QUEST-eligible residents who are not enrolled.

```python
from scripts.medquest import get_medquest_uninsured, search_medquest_uninsured
get_medquest_uninsured("senate", 1)
search_medquest_uninsured()  # ranked by uninsured rate
```

