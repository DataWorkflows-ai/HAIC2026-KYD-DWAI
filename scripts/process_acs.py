"""
Starter script to download and process ACS 2020-2024 5-year
House and Senate legislative district data for Hawaii.

Run from the repo root:
    python3 scripts/process_acs.py

Outputs clean CSVs to data/processed/
"""

import re
from typing import Optional

import requests
import pandas as pd
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Create directories
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Source URLs (from Hawaii State Data Center)
HOUSE_URL = "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_house_hi.xlsx"
SENATE_URL = "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_senate_hi.xlsx"

# Key labels from DP03 (economic characteristics)
DP03_LABELS = {
    "Population 16 years and over": "pop_16_plus",
    "In labor force": "in_labor_force",
    "Employed": "employed",
    "Median household income (dollars)": "median_hh_income",
    "Mean household income (dollars)": "mean_hh_income",
    "Per capita income (dollars)": "per_capita_income",
    "Median family income (dollars)": "median_family_income",
    "All families": "pct_families_poverty",
    "All people": "pct_people_poverty",
    "65 years and over": "pct_65plus_poverty",
    # Correct row under PEOPLE poverty section (not the "under 5 years only" family row)
    "Related children of the householder under 5 years": "pct_children_under5_poverty",
    # Overall uninsured (first occurrence under main HEALTH INSURANCE COVERAGE section)
    "No health insurance coverage": "pct_no_health_insurance",
}

# Key labels from DP04 (housing characteristics) for rent burden
DP04_LABELS = {
    "30.0 to 34.9 percent": "rent_30_to_34_9",
    "35.0 percent or more": "rent_35_plus",
}

def download_file(url: str, dest: Path) -> None:
    """Download a file if it does not already exist."""
    if dest.exists():
        print(f"Already exists: {dest}")
        return
    print(f"Downloading {url} ...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"Saved to {dest}")

def extract_district_number(name: str) -> Optional[int]:
    """Extract the numeric district ID from a name like 'State House District 22 (2024); Hawaii'."""
    if not isinstance(name, str):
        return None
    match = re.search(r"District\s+(\d+)", name, re.IGNORECASE)
    return int(match.group(1)) if match else None

def extract_metrics(excel_path: Path, sheet_name: str, labels: dict, chamber: str, prefer_first: bool = False) -> pd.DataFrame:
    """
    Generic extractor for wide-format ACS sheets (DP03 or DP04).
    Each district occupies 4 columns: estimate, MOE, percent, percent MOE.
    prefer_first=True takes the first match (useful for overall health insurance).
    """
    print(f"Reading {excel_path} sheet {sheet_name} ...")
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    # Row 0 contains district names in columns 1, 5, 9, 13, ...
    district_cols = []
    for col in range(1, df.shape[1], 4):
        district_name = df.iloc[0, col]
        if isinstance(district_name, str) and "District" in district_name:
            district_cols.append((col, district_name))

    print(f"  Found {len(district_cols)} districts")

    records = []
    for start_col, district_name in district_cols:
        district_num = extract_district_number(district_name)
        record = {
            "chamber": chamber,
            "district": district_num,
            "district_name": district_name,
        }

        for label, field in labels.items():
            mask = df[0].astype(str).str.contains(re.escape(label), case=False, na=False)
            matching_rows = df[mask]
            if matching_rows.empty:
                record[f"{field}_estimate"] = None
                record[f"{field}_moe"] = None
                record[f"{field}_percent"] = None
                record[f"{field}_percent_moe"] = None
                continue

            # under-5 poverty: always take LAST match so we get the people-level row
            if field == "pct_children_under5_poverty":
                row_idx = matching_rows.index[-1]
            # For health insurance and Employed we want the first (overall) match
            elif prefer_first or field in ("pct_no_health_insurance", "employed"):
                row_idx = matching_rows.index[0]
            else:
                row_idx = matching_rows.index[-1]

            record[f"{field}_estimate"] = df.iloc[row_idx, start_col]
            record[f"{field}_moe"] = df.iloc[row_idx, start_col + 1]
            record[f"{field}_percent"] = df.iloc[row_idx, start_col + 2]
            record[f"{field}_percent_moe"] = df.iloc[row_idx, start_col + 3]

        records.append(record)

    result = pd.DataFrame(records)
    print(f"  Extracted {len(result)} rows from {sheet_name}")
    return result

def main():
    house_raw = RAW_DIR / "acs2024_5yr_house_hi.xlsx"
    senate_raw = RAW_DIR / "acs2024_5yr_senate_hi.xlsx"

    download_file(HOUSE_URL, house_raw)
    download_file(SENATE_URL, senate_raw)

    # Extract DP03 (economic + health insurance + poverty)
    # prefer_first=True so we get the overall uninsured rate
    house_dp03 = extract_metrics(house_raw, "DP03", DP03_LABELS, "house", prefer_first=True)
    senate_dp03 = extract_metrics(senate_raw, "DP03", DP03_LABELS, "senate", prefer_first=True)

    # Extract DP04 (housing / rent burden) — last match is fine here
    house_dp04 = extract_metrics(house_raw, "DP04", DP04_LABELS, "house", prefer_first=False)
    senate_dp04 = extract_metrics(senate_raw, "DP04", DP04_LABELS, "senate", prefer_first=False)

    # Merge DP03 + DP04 on chamber + district
    house_merged = pd.merge(house_dp03, house_dp04, on=["chamber", "district", "district_name"], how="outer")
    senate_merged = pd.merge(senate_dp03, senate_dp04, on=["chamber", "district", "district_name"], how="outer")

    house_out = PROCESSED_DIR / "house_districts.csv"
    senate_out = PROCESSED_DIR / "senate_districts.csv"

    house_merged.to_csv(house_out, index=False)
    senate_merged.to_csv(senate_out, index=False)

    print(f"\nWrote {house_out}")
    print(f"Wrote {senate_out}")
    print("\nSample of house data (selected columns):")
    cols = ["district", "pct_no_health_insurance_percent", "pct_no_health_insurance_percent_moe", "pct_people_poverty_percent", "pct_people_poverty_percent_moe"]
    print(house_merged[cols].head(5).to_string())
    print("\nDone. Percent MOE columns are now included.")

if __name__ == "__main__":
    main()
