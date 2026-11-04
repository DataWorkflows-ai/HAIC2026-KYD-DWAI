# HAIC 2026 Know Your District – Project Status

**Goal:** Build an AI agent that gives legislative staff plain-language socio-economic summaries of Hawaii House and Senate districts, with citations, margins of error, and relevant program recommendations.

**End users:** Legislators and their offices.  
**Judges will not run scripts or set up databases** — the agent must be packaged as a clean module Mitchell can deploy in Streamlit.

**Personal repo:** https://github.com/crstllogan-blip/HAIC-Know-Your-District  
**DataWorkflows repo:** https://github.com/DataWorkflows-ai/HAIC2026-KYD-DWAI

---

## Completed

### Data sources
- `data_sources.md` documents all key public sources (ACS Excels, DOTAX, UHERO, Data Book, SNAP, Med-QUEST, HPHA, early childhood programs, GIS boundaries, etc.).

### ACS data pipeline
- `scripts/process_acs.py` downloads the official 2020–2024 5-year House and Senate Excel files and extracts clean metrics from the wide-format DP03 and DP04 sheets.
- Processed CSVs and SQLite database (`data/districts.db`) are ready.
- Metrics include income, poverty (including 65+ and children under 5), overall uninsured rate, and rent burden bands.

### Minimal agent (Streamlit-ready)
- `scripts/agent.py` is a clean module with:
  - `get_district(chamber, district_number)` 
  - `answer(question)` that returns plain-language text with citations and official program links
- Fixed bugs:
  - Kūpuna logic now requires both the district and the age/poverty terms (parentheses added).
  - Rent burden >30% now sums the 30–34.9% and 35%+ bands.
- Covers all five test questions and includes program links (SNAP, Med-QUEST, HPHA, EOEL, LIHEAP) as required by the challenge.

### Test questions
- `data/test_questions.md` contains the five staffer questions with verified answers, citations, warnings, and program links.

### Sharing
- Everything is pushed to the personal repo.
- Local commit exists in the DataWorkflows clone; push is blocked pending write access.

---

## Next steps

### Immediate
1. Get write access to `DataWorkflows-ai/HAIC2026-KYD-DWAI` and push the local commit so Mitchell can pull a ready-to-use module.
2. Add a thin Streamlit wrapper (`app.py`) that imports `answer()` from `scripts/agent.py` so Mitchell can deploy it with one command.
3. Include the Honolulu County (Oʻahu) 65+ poverty rate as a comparison in the HD 22 answer.

### Short-term
- Expand program recommendations with more official links and brief eligibility notes.
- Surface margins of error more clearly in answers.
- Add a simple district selector or example questions in the Streamlit UI for legislators and staff.

### Longer-term (per use-case PDF)
- Incorporate additional sources where useful (DOTAX, UHERO, Data Book, county-level SNAP totals).
- Add district boundary mapping.
- Handle data limitations and confidence intervals more explicitly.
- Replace or augment the rule-based logic with an LLM that calls the same `get_district()` / SQL tools if desired.

---

## How to run what exists today

```bash
# Load CSVs into SQLite (already done)
python3 scripts/load_sqlite.py

# Test the agent
python3 scripts/agent.py
```

The `answer()` function is ready to be imported into a Streamlit app.

---

*Last updated: 2026-11-02*
