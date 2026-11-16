"""Demographic breakdowns (currently unemployment by sex, age, race/ethnicity, education; ACS 2020–2024).

Read-only access to the `breakdown` table in kyd.sqlite (built by etl/load_unemp_demographics.py). Every row has an
obs_id, value (rate %) and MOE, so the System-2 number check can trace any figure the agent quotes. Rows the
research file flags `high_moe` (CV ≥ 30% etc.) carry the existing `suppressed_cv` flag and are shown greyed.
"""
from __future__ import annotations
import json
import sqlite3
from functools import lru_cache

from ..config import settings
from .cache import cached

DIMENSIONS = {  # dimension → (label, which sex rows to show)
    "overall": ("All workers 16+", ("both",)),
    "sex": ("By sex", ("male", "female")),
    "age_collapsed": ("By age", ("both",)),
    "race_ethnicity": ("By race and ethnicity", ("both",)),
    "education": ("By education (ages 25–64)", ("both",)),
}
COUNTY_FIPS = {"Oahu": "15003", "Hawaii": "15001", "Maui": "15009", "Kauai": "15007"}
NOTES = ["ACS 2020–2024 5-year averages with 90% margins of error; the newest year is 2024.",
         "Greyed cells have high uncertainty (coefficient of variation ≥ 30% or margin ≥ the rate). Treat as unreliable.",
         "Education rates cover ages 25–64 only and are not comparable to the 16+ rates.",
         "Rates rebuilt from Census tables B23025, B23001, C23002A–I and B23006 (S2301 is not in the keyless files)."]


@lru_cache(maxsize=1)
def _rows() -> dict[str, list[dict]]:
    p = settings().data_dir / "kyd.sqlite"
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        out: dict[str, list[dict]] = {}
        for r in c.execute("SELECT * FROM breakdown WHERE topic = 'unemployment'"):
            out.setdefault(r["geo_id"], []).append(dict(r))
        return out
    except sqlite3.OperationalError:
        return {}
    finally:
        c.close()


def _shape(r: dict) -> dict:
    label = ("All workers 16+" if r["dimension"] == "overall" else r["grp"]) if r["sex"] == "both" else r["sex"].capitalize()
    return {"obs_id": r["obs_id"], "geo_id": r["geo_id"], "dimension": r["dimension"], "group": r["grp"],
            "sex": r["sex"], "label": label, "value": r["value"], "moe": r["moe"], "unit": "pct",
            "unemployed": r["numerator"], "labor_force": r["denominator"], "source_table": r["source_table"],
            "flags": ["suppressed_cv"] if r["quality_flag"] == "high_moe" else [], "vintage": r["vintage"],
            "source_id": r["source_id"]}


def _for(geo_id: str, dims: list[str]) -> dict[str, list[dict]]:
    out = {}
    for d in dims:
        sexes = DIMENSIONS[d][1]
        rows = [_shape(r) for r in _rows().get(geo_id, []) if r["dimension"] == d and r["sex"] in sexes]
        if d == "age_collapsed":
            rows.sort(key=lambda x: int(x["group"].split()[0]))
        out[d] = rows
    return out


@cached
def unemployment(geo_id: str, dimension: str = "all") -> dict:
    """District (or county/state) unemployment breakdowns with the matching county and state rows."""
    if geo_id not in _rows():
        raise KeyError(geo_id)
    dims = list(DIMENSIONS) if dimension == "all" else [dimension]
    if any(d not in DIMENSIONS for d in dims):
        raise ValueError(f"dimension must be one of {', '.join(DIMENSIONS)} or 'all'")
    counties = json.loads((settings().data_dir / "district_counties.json").read_text())
    cg = f"CNTY-{COUNTY_FIPS[counties[geo_id]]}" if geo_id in counties else None
    return {"geo_id": geo_id, "county_geo_id": cg, "dimensions": {d: DIMENSIONS[d][0] for d in dims},
            "rows": _for(geo_id, dims), "county": _for(cg, dims) if cg else {}, "state": _for("HI", dims),
            "notes": NOTES, "source": "U.S. Census Bureau, ACS 2020–2024 5-year (B23025, B23001, C23002A–I, B23006)"}
