# HAIC 2026 Know Your District – Project Status

**Goal:** Build an AI agent that gives legislative staff plain-language socio-economic summaries of Hawaii House and Senate districts, with citations, margins of error, and relevant program recommendations.

**Repo:** https://github.com/crstllogan-blip/HAIC-Know-Your-District

---

## What is done

### Data sources documented
- `data_sources.md` lists all key public sources (ACS Excels, DOTAX, UHERO, Data Book, SNAP, Med-QUEST, HPHA, early childhood programs, GIS boundaries, etc.).

### ACS data processed
- Script: `scripts/process_acs.py`
- Downloads the official 2020–2024 5-year House and Senate Excel files from the Hawaii State Data Center.
- Parses the wide-format DP03 (economic) and DP04 (housing) sheets.
- Extracts key metrics per district into clean CSVs:
  - `data/processed/house_districts.csv` (51 districts)
  - `data/processed/senate_districts.csv` (25 districts)
- Current metrics include: population 16+, labor force, median/mean household income, per capita income, median family income, poverty rates (families, people, 65+, children under 5), health insurance (no coverage), and rent burden (30–34.9% and 35%+).

### Lookup function
- `scripts/lookup.py` contains `get_district(chamber, district_number)` that returns a dictionary of metrics for any House or Senate district.
- Usage example is documented in the main `README.md`.

### Test questions
- `data/test_questions.md` contains five realistic staffer questions with example answers, citations, warnings, and program links:
  1. Kūpuna poverty in HD 22 vs. Oʻahu
  2. SNAP eligibility vs. enrollment in SD 12
  3. Top 3 House districts by uninsured rate
  4. Rent burden >30% of income
  5. Children under 5 in poverty in HD 45

---

## Current process (how the data pipeline works)

1. Run `python3 scripts/process_acs.py` to download (if needed) and regenerate the clean CSVs from the official Excels.
2. The script matches row labels in DP03 and DP04 and writes one tidy row per district.
3. `scripts/lookup.py` loads those CSVs and returns data for a specific district.
4. An agent (or evaluation script) can call `get_district()` and cite the source as “ACS 2020–2024 5-year, DP03/DP04, Hawaii State Data Center.”

---

## Known gaps / next steps

### Immediate (to fully answer the 5 test questions)
- Verify that the health insurance and rent-burden columns are populated after the latest script run. If labels did not match, inspect the exact wording in the DP03/DP04 sheets and update `DP03_LABELS` / `DP04_LABELS` in `process_acs.py`, then re-run.
- Confirm the numbers in `data/test_questions.md` against the regenerated CSVs (especially questions 3 and 4).
- Add the Honolulu County (Oʻahu) 65+ poverty rate as a comparison value (available from S1701).

### Short-term
- Expand extraction if needed (more age breaks, housing cost burden details, etc.).
- Decide how the agent will access the data:
  - Simple: import `get_district()` and call it from the agent’s tools.
  - Alternative: load the CSVs into SQLite and give the agent a SQL tool.
- Build a minimal agent prototype that can answer the five test questions with citations and program links.

### Longer-term (per use-case PDF)
- Incorporate additional sources where useful (DOTAX tax statistics, UHERO reports, Data Book tables, SNAP participation at county level).
- Add district boundary mapping (shapefiles already linked in `data_sources.md`).
- Handle margins of error and data limitations explicitly in answers.
- Create a web chat interface.

---

## How to continue with a Grok bot

1. Point the bot at this repo: https://github.com/crstllogan-blip/HAIC-Know-Your-District
2. Tell it to read `PROJECT_STATUS.md`, `data_sources.md`, and `data/test_questions.md`.
3. Ask it to help verify/fix the remaining label matches, confirm the test-question answers, or wire `get_district()` into a simple agent.

---

*Last updated: 2026-11-02*
