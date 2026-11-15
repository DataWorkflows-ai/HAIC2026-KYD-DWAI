# SNAP Analytical Framework

District-level enrolled-vs-eligible gap analysis for SNAP in Hawaiʻi House and Senate districts.

**Data years:** ACS 2020–2024 5-year estimates  
**Geography:** Hawaii legislative districts (51 House, 25 Senate)

## Data Inputs

| Table | Role | What it supplies | Files |
|-------|------|------------------|-------|
| **S2201** | Enrolled demographic profile | Count and characteristics of households receiving SNAP in each district: race/ethnicity of householder, age composition, disability status, poverty status of recipients, household type, etc. | `data/raw/S2201_senate_districts.json`, `data/raw/S2201_house_districts.json` |
| **S1701** | Income-eligible population | People below 130% of the federal poverty level (SNAP gross-income threshold) by race/ethnicity, age, education, employment status, and other characteristics, for each district. | `data/raw/S1701_senate_districts.json`, `data/raw/S1701_house_districts.json` |
| **S1810** | Disability context | Disability by type (hearing, vision, cognitive, ambulatory, self-care, independent living) at the district level. SNAP has special rules for elderly and disabled households. | `data/raw/S1810_senate_districts.json`, `data/raw/S1810_house_districts.json` |
| **DP03** | Broader economic context | Employment, commute, occupation, industry, income, health insurance, and poverty by district. | `data/raw/DP03_senate_districts.json`, `data/raw/DP03_house_districts.json` |
| District boundary GeoJSON | Mapping | Official House and Senate district boundaries already in the repo. Join on chamber + district id. | `data/boundaries/senate_2022.geojson`, `data/boundaries/house_2022.geojson` |

## Steps

### 1. Extract enrolled profile (S2201)

For each district, pull from S2201. Official column mapping (verified against Census API labels and Senate District 1 values):

| Column | Official meaning | Use |
|--------|------------------|-----|
| `C01_001E` | Total households | Denominator for overall receipt rate |
| `C03_001E` | Households receiving SNAP | Enrolled count |
| **`C04_001E`** | **Percent households receiving food stamps/SNAP** | **SNAP receipt rate** (share of all households that receive SNAP). First row only. |
| `C01_xxxE` | Total households with characteristic xxx | Denominator for within-group receipt rate |
| `C02_xxxE` | Percent of all households with characteristic xxx | Composition of the district, not a SNAP rate |
| `C03_xxxE` | SNAP households with characteristic xxx | Enrolled count for that group |
| **`C04_xxxE`** | **Percent of SNAP households with characteristic xxx** | Composition of the enrolled group. **Not** the receipt rate within the group. |

**Critical percent-column rule (confirmed):**

- **First row (Households / `_001`)**: `C04_001E` = share of **all** households that receive SNAP. This is the SNAP receipt rate.
- **Every other row**: `C04_xxxE` = share of **SNAP-receiving households** that have that characteristic (e.g. “share of SNAP households with someone 60+”). This is **not** the SNAP receipt rate within that group.
- **Receipt rate within a group** = that group’s SNAP count (`C03_xxxE`) ÷ that group’s total count (`C01_xxxE`).

Example (Senate District 1):
- Overall receipt rate: `C04_001E` = 20.1% (3,992 / 19,872)
- Share of SNAP households with someone 60+: `C04_002E` = 42.7% (1,703 / 3,992)
- Receipt rate among households with someone 60+: 1,703 / 10,919 = 15.6% (must be calculated; not stored in `C04`)

Always retain the corresponding margins of error (`M` suffix).

### 2. Extract income-eligible population (S1701)

For each district, pull from S1701:

- Counts of people below 200% of the federal poverty level (Hawaii SNAP gross-income limit per the DHS Databook; use `C01_042E`)
- Broken down by race/ethnicity, age, education, employment status, and other available characteristics
- Retain margins of error

This is the eligibility proxy. It overcounts true eligibility because SNAP also has asset tests, citizenship/immigration rules, and categorical eligibility, but it is the best public approximation available at district level.

### 3. Compute the gap (counts only)

**Use counts. Do not use percent columns.**

| Source | Count column to use | Do not use |
|--------|---------------------|------------|
| S2201 | `C03_001E` — households receiving SNAP | `C04` — percent (composition of SNAP households, or overall receipt rate on the total row) |
| S1701 | `C01_042E` — people below 200% of poverty (Hawaii SNAP gross-income limit per DHS Databook) | `C03` — percent below poverty |

```
gap = S1701 people below 200% FPL (C01_042E)
    − S2201 SNAP households (C03_001E)
```

The residual is the estimated eligible-but-not-enrolled figure. It mixes people and households, so it is an estimate, not a measured caseload. Always return that caveat with the number.

`scripts/snap_gap.py` implements this. `get_snap_gap()` reads only the count columns and records the percent columns under `not_used`.

### 4. Compare demographics

Contrast the composition of:

- **Enrolled group** (from S2201): race/ethnicity, age, disability profile of SNAP households
- **Eligible-but-not-enrolled group** (S1701 minus S2201): same characteristics for the residual population

Highlight groups that are over- or under-represented among the enrolled relative to the eligible-but-not-enrolled population. These differences point to possible outreach opportunities.

### 5. Map the gaps

Join the district-level gap estimates to the official legislative district boundary GeoJSON:

- Senate: Hawaii GeoPortal AdminBnd layer for Senate districts
- House: Hawaii GeoPortal AdminBnd layer for House districts

Produce maps that show where the enrollment gap is largest, both in absolute numbers and as a rate.

## Output

For each district the analysis should produce:

- SNAP enrolled count and rate (with MOE)
- Estimated income-eligible population (with MOE)
- Estimated eligible-but-not-enrolled residual (with MOE and caveat)
- Demographic comparison of enrolled vs. eligible-but-not-enrolled
- Map layer of gap size / rate

## Caveats (must appear with every result)

- All figures are ACS sample estimates and carry margins of error.
- District populations are modest; detailed cells have wide confidence intervals.
- “Eligible but not enrolled” is an estimate based on income-to-poverty ratio only. Actual SNAP eligibility also depends on assets, household composition, work requirements, and immigration status.
- S2201 counts households; S1701 primarily counts people. Align units carefully and note any household-to-person conversion assumptions.
- Self-reported Census SNAP receipt can differ from administrative caseload counts.

## Next Implementation Steps

1. Parse the four JSON files into tidy district-level tables.
2. Align common demographic dimensions between S2201 and S1701.
3. Calculate gaps and MOEs.
4. Store results in the project database for the agent.
5. Attach GeoJSON and generate map outputs.
