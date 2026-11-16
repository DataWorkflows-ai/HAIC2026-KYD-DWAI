"""2020 census tract → 2022 legislative district crosswalk, weighted by 2020 population.

  python kyd/etl/build_tract_crosswalk.py

Inputs (fetched from the Hawaiʻi Statewide GIS Program if missing; SHA-256 recorded next to each file):
  data/raw/gis/tracts20.geojson   2020 Census Tracts      (Census/MapServer/31)
  data/raw/gis/bg20.geojson       2020 Census Block Groups with pop20 (Census/MapServer/26)
  data/raw/gis/house22.geojson, senate22.geojson   2022 districts (already in the repo)

Method: each block group is split across districts by area; its 2020 population follows the area
shares. A tract's weight in a district = population of the tract's block-group pieces in that district
÷ tract population. Population weighting matters in Hawaiʻi, where large rural tracts hold few people.
Tracts with no population fall back to area shares.

Outputs: kyd/data/tract_district_crosswalk.csv  (tract, chamber, geo_id, weight, tract_pop20)
         kyd/data/bg_district_crosswalk.csv     (bg, chamber, geo_id, area_share, pop20_allocated) — block-group pieces
"""
from __future__ import annotations
import csv
import hashlib
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely.validation import make_valid

REPO = Path(__file__).resolve().parents[2]
GIS = REPO / "data" / "raw" / "gis"
OUT = REPO / "kyd" / "data" / "tract_district_crosswalk.csv"
OUT_BG = REPO / "kyd" / "data" / "bg_district_crosswalk.csv"
SERVICE = "https://geodata.hawaii.gov/arcgis/rest/services/Census/MapServer"
LAYERS = {"tracts20": (31, "geoid20,county,island,pop20,aland20"), "bg20": (26, "geoid20,pop20,aland20")}


def _fetch(name: str) -> dict:
    path = GIS / f"{name}.geojson"
    if not path.exists():
        layer, fields = LAYERS[name]
        feats, off = [], 0
        while True:
            q = urllib.parse.urlencode({"where": "1=1", "outFields": fields, "outSR": 4326, "f": "geojson",
                                        "resultOffset": off, "resultRecordCount": 1000, "orderByFields": "objectid"})
            d = json.load(urllib.request.urlopen(f"{SERVICE}/{layer}/query?{q}", timeout=120))
            feats += d["features"]
            if len(d["features"]) < 1000:
                break
            off += 1000
        path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    (GIS / f"{name}.geojson.sha256").write_text(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}.geojson\n")
    return json.loads(path.read_text())


def _geom(f):
    g = shape(f["geometry"])
    return g if g.is_valid else make_valid(g)


def build() -> int:
    tracts = {f["properties"]["geoid20"]: f["properties"] for f in _fetch("tracts20")["features"]}
    tract_geom = {f["properties"]["geoid20"]: _geom(f) for f in _fetch("tracts20")["features"]}
    bgs = [(f["properties"]["geoid20"], f["properties"]["pop20"] or 0, _geom(f)) for f in _fetch("bg20")["features"]]
    rows, bg_rows = [], []
    for chamber, fname, key, prefix in (("house", "house22.geojson", "house_id", "HD"),
                                        ("senate", "senate22.geojson", "senate_id", "SD")):
        dist = [(f"{prefix}-{int(f['properties'][key]):02d}", _geom(f))
                for f in json.loads((GIS / fname).read_text())["features"]]
        tree = STRtree([g for _, g in dist])

        def split(g):   # area shares of geometry g across districts
            parts = {}
            for i in tree.query(g):
                a = g.intersection(dist[i][1]).area
                if a > 0:
                    parts[dist[i][0]] = parts.get(dist[i][0], 0) + a
            tot = sum(parts.values())
            return {k: v / tot for k, v in parts.items()} if tot else {}

        pop = defaultdict(lambda: defaultdict(float))
        for bg_id, p, g in bgs:
            for d, s in split(g).items():
                pop[bg_id[:11]][d] += p * s
                if s >= 0.0005:
                    bg_rows.append((bg_id, chamber, d, round(s, 4), round(p * s, 1)))
        for t, props in tracts.items():
            tp = sum(pop[t].values())
            w = {d: v / tp for d, v in pop[t].items()} if tp > 0 else split(tract_geom[t])
            for d, v in sorted(w.items()):
                if v >= 0.0005:
                    rows.append((t, chamber, d, round(v, 4), props["pop20"] or 0))
    with OUT.open("w", newline="") as f:
        csv.writer(f).writerows([("tract", "chamber", "geo_id", "weight", "tract_pop20"), *rows])
    with OUT_BG.open("w", newline="") as f:
        csv.writer(f).writerows([("bg", "chamber", "geo_id", "area_share", "pop20_allocated"), *bg_rows])
    print(f"{OUT.relative_to(REPO)}: {len(tracts)} tracts, {len(rows)} tract-district pieces; "
          f"{OUT_BG.relative_to(REPO)}: {len(bg_rows)} block-group pieces")
    return len(rows)


if __name__ == "__main__":
    build()
