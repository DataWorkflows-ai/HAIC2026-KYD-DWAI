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

# Key labels from DP02 (social characteristics)
DP02_LABELS = {
    # First "65 years and over" under Householder living alone = overall 65+ living alone
    "65 years and over": "householders_65plus_living_alone",
    # First "With a disability" under DISABILITY STATUS = overall disability
    "With a disability": "with_disability",
    # First "Speak English less than very well" = overall limited English
    'Speak English less than "very well"': "limited_english",
}

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
    "Related children of the householder under 5 years": "pct_children_under5_poverty",
    "No health insurance coverage": "pct_no_health_insurance",
    "With Food Stamp/SNAP benefits in the past 12 months": "snap_benefits",
}

# Key labels from DP04 (housing characteristics)
DP04_LABELS = {
    "30.0 to 34.9 percent": "rent_30_to_34_9",
    "35.0 percent or more": "rent_35_plus",
    "No vehicles available": "no_vehicle",
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
    Generic extractor for wide-format ACS sheets (DP02, DP03, or DP04).
    Each district occupies 4 columns: estimate, MOE, percent, percent MOE.
    prefer_first=True takes the first match (useful for overall rates).
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

            # Special cases: under-5 poverty takes LAST match (people-level row)
            if field == "pct_children_under5_poverty":
                row_idx = matching_rows.index[-1]
            # These take first match for the overall (not age/tenure subgroup) figure
            elif prefer_first or field in (
                "pct_no_health_insurance",
                "employed",
                "householders_65plus_living_alone",
                "with_disability",
                "limited_english",
                "snap_benefits",
                "no_vehicle",
            ):
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

    # Extract DP02 (social: 65+ alone, disability, limited English)
    house_dp02 = extract_metrics(house_raw, "DP02", DP02_LABELS, "house", prefer_first=True)
    senate_dp02 = extract_metrics(senate_raw, "DP02", DP02_LABELS, "senate", prefer_first=True)

    # Extract DP03 (economic + health insurance + poverty + SNAP)
    house_dp03 = extract_metrics(house_raw, "DP03", DP03_LABELS, "house", prefer_first=True)
    senate_dp03 = extract_metrics(senate_raw, "DP03", DP03_LABELS, "senate", prefer_first=True)

    # Extract DP04 (housing / rent burden / no vehicle)
    house_dp04 = extract_metrics(house_raw, "DP04", DP04_LABELS, "house", prefer_first=True)
    senate_dp04 = extract_metrics(senate_raw, "DP04", DP04_LABELS, "senate", prefer_first=True)

    # Merge all on chamber + district
    house_merged = pd.merge(house_dp02, house_dp03, on=["chamber", "district", "district_name"], how="outer")
    house_merged = pd.merge(house_merged, house_dp04, on=["chamber", "district", "district_name"], how="outer")

    senate_merged = pd.merge(senate_dp02, senate_dp03, on=["chamber", "district", "district_name"], how="outer")
    senate_merged = pd.merge(senate_merged, senate_dp04, on=["chamber", "district", "district_name"], how="outer")

    house_out = PROCESSED_DIR / "house_districts.csv"
    senate_out = PROCESSED_DIR / "senate_districts.csv"

    house_merged.to_csv(house_out, index=False)
    senate_merged.to_csv(senate_out, index=False)

    print(f"\nWrote {house_out}")
    print(f"Wrote {senate_out}")
    print("\nSample of house data (persona columns):")
    cols = [
        "district",
        "householders_65plus_living_alone_percent",
        "with_disability_percent",
        "limited_english_percent",
        "snap_benefits_percent",
        "no_vehicle_percent",
    ]
    print(house_merged[cols].head(5).to_string())
    print("\nDone. Persona metrics (65+ alone, disability, limited English, SNAP, no vehicle) are included.")

if __name__ == "__main__":
    main()
