# HAIC2026-KYD-DWAI
HAIC 2026 Challenge: Know Your District

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
