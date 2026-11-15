"""Who represents each district, and how House and Senate districts overlap.

  data/legislators.csv       one row per seat, with source and status
                             (official | secondary | verify | pending); party is intentionally omitted
  data/district_overlap.csv  area-weighted House↔Senate overlap from etl/load_boundaries.py

The two chambers' districts do not nest, so a House district can fall in
several Senate districts and the reverse. Every counterpart is listed with the
share of overlap.
"""
from __future__ import annotations
import csv
import json
from functools import lru_cache
from ..config import settings

ROSTER_AS_OF = "2026-11-13"
OVERLAP_METHOD = ("Share of land area (2022 boundaries, Hawaiʻi Statewide GIS Program). "
                  "Population-weighted shares will replace this once 2020 block weights are loaded.")


@lru_cache
def _members() -> dict[str, dict]:
    with (settings().data_dir / "legislators.csv").open(encoding="utf-8") as f:
        return {r["geo_id"]: r for r in csv.DictReader(f)}


@lru_cache
def _overlap() -> list[dict]:
    p = settings().data_dir / "district_overlap.csv"
    if not p.exists():
        return []
    with p.open() as f:
        return [{**r, "share_of_house": float(r["share_of_house"]), "share_of_senate": float(r["share_of_senate"])}
                for r in csv.DictReader(f)]


LOCAL_METHOD = ("Neighborhoods: Honolulu Board of Realtors areas (City & County of Honolulu, 2012) on Oʻahu, "
                "USGS GNIS populated places elsewhere. Boards: Honolulu Neighborhood Plan (2008). Council districts: "
                "Hawaiʻi Statewide GIS Program. Matched by area overlap with 2022 district boundaries.")


@lru_cache
def _local() -> dict[str, dict]:
    p = settings().data_dir / "district_local.json"
    return json.loads(p.read_text(encoding="utf-8"))["districts"] if p.exists() else {}


def local_areas(geo_id: str) -> dict:
    """Neighborhoods, Oʻahu neighborhood boards and county council districts inside a legislative district."""
    return _local().get(geo_id, {"neighborhoods": [], "boards": [], "council": []})


def member(geo_id: str) -> dict | None:
    m = _members().get(geo_id)
    if not m:
        return None
    return {"geo_id": geo_id, "name": m["name"] or None, "title": "Senator" if geo_id.startswith("SD") else "Representative",
            "basis": m["basis"], "status": m["status"], "source": m["source"] or None,
            "source_url": m["source_url"] or None, "note": m["note"] or None}


def counterparts(geo_id: str) -> list[dict]:
    """Senate districts overlapping a House district, or the reverse, largest share first."""
    out = []
    for r in _overlap():
        if geo_id == r["house_geo"]:
            other, mine, theirs = r["senate_geo"], r["share_of_house"], r["share_of_senate"]
        elif geo_id == r["senate_geo"]:
            other, mine, theirs = r["house_geo"], r["share_of_senate"], r["share_of_house"]
        else:
            continue
        out.append({"geo_id": other, "share_of_this": mine, "share_of_other": theirs, "member": member(other)})
    return sorted(out, key=lambda x: -x["share_of_this"])


def representation(geo_id: str) -> dict:
    return {"geo_id": geo_id, "member": member(geo_id), "counterparts": counterparts(geo_id),
            **local_areas(geo_id), "roster_as_of": ROSTER_AS_OF, "overlap_method": OVERLAP_METHOD,
            "local_method": LOCAL_METHOD}


def roster_summary() -> dict:
    ms = _members().values()
    counts: dict[str, int] = {}
    for m in ms:
        counts[m["status"]] = counts.get(m["status"], 0) + 1
    return {"as_of": ROSTER_AS_OF, "counts": counts}
