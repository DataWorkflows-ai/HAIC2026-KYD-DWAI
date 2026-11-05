"""
Process ACS 2020-2024 5-year House and Senate legislative district data for Hawaii.

Run from the repo root:
    python3 scripts/process_acs.py

Outputs clean CSVs to data/processed/
"""

import math
import re
from typing import Optional

import requests
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

HOUSE_URL = "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_house_hi.xlsx"
SENATE_URL = "https://files.hawaii.gov/dbedt/census/acs/acs2024/5yr/acs2024_5yr_senate_hi.xlsx"

DP02_LABELS = {
    "With a disability": "with_disability",
    'Speak English less than "very well"': "limited_english",
}

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

DP04_LABELS = {
    "30.0 to 34.9 percent": "rent_30_to_34_9",
    "35.0 percent or more": "rent_35_plus",
    "No vehicles available": "no_vehicle",
}

def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"Already exists: {dest}")
        return
    print(f"Downloading {url} ...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"Saved to {dest}")

def extract_district_number(name: str) -> Optional[int]:
    if not isinstance(name, str):
        return None
    match = re.search(r"District\s+(\d+)", name, re.IGNORECASE)
    return int(match.group(1)) if match else None

def _num(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).replace(",", "").replace("±", "").replace("%", "").strip()
    if s in ("(X)", "", "nan", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def compute_65plus_alone(df, start_col):
    """
    Sum male + female householders 65+ living alone.
    Returns (estimate, moe, percent_str, percent_moe_str, raw_pct).
    raw_pct is the unrounded percent (e.g. 17.234) for ranking.
    """
    male_row = None
    female_row = None
    total_hh_row = None

    for i in range(len(df)):
        label = str(df.iloc[i, 0])
        if label == "Total households" and total_hh_row is None:
            total_hh_row = i
        if label == "Male householder, no spouse/partner present":
            for j in range(i + 1, min(i + 6, len(df))):
                if str(df.iloc[j, 0]) == "65 years and over":
                    male_row = j
                    break
        if label == "Female householder, no spouse/partner present":
            for j in range(i + 1, min(i + 6, len(df))):
                if str(df.iloc[j, 0]) == "65 years and over":
                    female_row = j
                    break

    if male_row is None or female_row is None or total_hh_row is None:
        return None, None, None, None, None

    male_est = _num(df.iloc[male_row, start_col]) or 0
    male_moe = _num(df.iloc[male_row, start_col + 1]) or 0
    female_est = _num(df.iloc[female_row, start_col]) or 0
    female_moe = _num(df.iloc[female_row, start_col + 1]) or 0
    total_hh = _num(df.iloc[total_hh_row, start_col]) or 0
    total_hh_moe = _num(df.iloc[total_hh_row, start_col + 1]) or 0

    est = male_est + female_est
    moe = math.sqrt(male_moe ** 2 + female_moe ** 2)

    if total_hh == 0:
        return est, moe, None, None, None

    pct = est / total_hh
    under = moe ** 2 - (pct ** 2) * (total_hh_moe ** 2)
    if under < 0:
        pct_moe = moe / total_hh
    else:
        pct_moe = math.sqrt(under) / total_hh

    raw_pct = pct * 100
    return est, moe, f"{raw_pct:.1f}%", f"±{pct_moe * 100:.1f}", raw_pct

def extract_metrics(excel_path: Path, sheet_name: str, labels: dict, chamber: str, prefer_first: bool = False) -> pd.DataFrame:
    print(f"Reading {excel_path} sheet {sheet_name} ...")
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

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

        if sheet_name == "DP02":
            est, moe, pct, pct_moe, raw_pct = compute_65plus_alone(df, start_col)
            record["householders_65plus_living_alone_estimate"] = est
            record["householders_65plus_living_alone_moe"] = f"±{moe:.0f}" if moe else None
            record["householders_65plus_living_alone_percent"] = pct
            record["householders_65plus_living_alone_percent_moe"] = pct_moe
            record["householders_65plus_living_alone_raw_pct"] = raw_pct

        for label, field in labels.items():
            mask = df[0].astype(str).str.contains(re.escape(label), case=False, na=False)
            matching_rows = df[mask]
            if matching_rows.empty:
                record[f"{field}_estimate"] = None
                record[f"{field}_moe"] = None
                record[f"{field}_percent"] = None
                record[f"{field}_percent_moe"] = None
                continue

            if field == "pct_children_under5_poverty":
                row_idx = matching_rows.index[-1]
            elif prefer_first or field in (
                "pct_no_health_insurance",
                "employed",
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

    house_dp02 = extract_metrics(house_raw, "DP02", DP02_LABELS, "house", prefer_first=True)
    senate_dp02 = extract_metrics(senate_raw, "DP02", DP02_LABELS, "senate", prefer_first=True)

    house_dp03 = extract_metrics(house_raw, "DP03", DP03_LABELS, "house", prefer_first=True)
    senate_dp03 = extract_metrics(senate_raw, "DP03", DP03_LABELS, "senate", prefer_first=True)

    house_dp04 = extract_metrics(house_raw, "DP04", DP04_LABELS, "house", prefer_first=True)
    senate_dp04 = extract_metrics(senate_raw, "DP04", DP04_LABELS, "senate", prefer_first=True)

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
    print("\n65+ living alone check (should match expected):")
    for d in [22, 5, 30, 45]:
        row = house_merged[house_merged.district == d]
        if not row.empty:
            r = row.iloc[0]
            print(f"  HD{d}: {r['householders_65plus_living_alone_percent']} {r['householders_65plus_living_alone_percent_moe']} ({r['householders_65plus_living_alone_estimate']}) raw={r['householders_65plus_living_alone_raw_pct']:.2f}")
    print("\nDone.")

if __name__ == "__main__":
    main()
