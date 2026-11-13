"""2022 legislative district boundaries → archived raw files, app GeoJSON, House↔Senate overlap.

Source: Hawaii Statewide GIS Program, ArcGIS REST service AdminBnd/MapServer
  layer 33 = State House Districts 22, layer 34 = State Senate Districts 22.

  python kyd/etl/load_boundaries.py            # use data/raw/gis/*.geojson if present
  python kyd/etl/load_boundaries.py --fetch    # re-download first

Outputs
  data/raw/gis/{house22,senate22}.geojson    raw archive, with a .sha256 file next to each
  kyd/frontend/public/geo/{sldl,sldu}.geojson   simplified boundaries, used as the fallback map layer
  kyd/data/district_overlap.csv              house_geo, senate_geo, share_of_house, share_of_senate

Overlap is computed by AREA in an equal-area projection. Because population is
not spread evenly over land, this is an approximation until the 2020-block
population weights are built (decision doc §2.4). Slivers under 1% are dropped;
they come from digitizing differences along shared edges.
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
import numpy as np
import shapely
from shapely.geometry import mapping, shape

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw" / "gis"
OUT_GEO = REPO / "kyd" / "frontend" / "public" / "geo"
OUT_DATA = REPO / "kyd" / "data"
SERVICE = "https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer"
LAYERS = {"house22": 33, "senate22": 34}
SLIVER = 0.01
# Hawaii Albers Equal Area Conic (ESRI:102007)
_T = Transformer.from_crs("EPSG:4326", "ESRI:102007", always_xy=True)


def to_eq(g):
    return shapely.transform(g, lambda c: np.column_stack(_T.transform(c[:, 0], c[:, 1])))


def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, layer in LAYERS.items():
        url = f"{SERVICE}/{layer}/query?outFields=*&where=1%3D1&f=geojson"
        with urllib.request.urlopen(url, timeout=120) as r:
            (RAW / f"{name}.geojson").write_bytes(r.read())
        print("fetched", name)


def archive_meta(name: str) -> dict:
    p = RAW / f"{name}.geojson"
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    (RAW / f"{name}.geojson.sha256").write_text(f"{digest}  {p.name}\n")
    return {"file": str(p.relative_to(REPO)), "sha256": digest,
            "source": f"{SERVICE}/{LAYERS[name]}",
            "retrieved_at": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}


def load(name: str, id_field: str, prefix: str) -> dict[str, dict]:
    fc = json.loads((RAW / f"{name}.geojson").read_text())
    out = {}
    for f in fc["features"]:
        p = f["properties"]
        gid = f"{prefix}-{int(p[id_field]):02d}"
        out[gid] = {"geom": shape(f["geometry"]), "county": (p.get("county") or "").title(), "props": p}
    return out


def write_app_geojson(feats: dict[str, dict], chamber: str, label: str) -> None:
    OUT_GEO.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": gid,
         "properties": {"geo_id": gid, "name": f"{label} District {int(gid[3:])}", "county": v["county"]},
         "geometry": mapping(v["geom"].simplify(0.0003, preserve_topology=True))}   # ~30 m
        for gid, v in sorted(feats.items())]}
    p = OUT_GEO / f"{chamber}.geojson"
    p.write_text(json.dumps(fc, separators=(",", ":")))
    print(f"{p.relative_to(REPO)}: {p.stat().st_size // 1024} KB")


def overlaps(house: dict, senate: dict) -> list[dict]:
    H = {k: to_eq(v["geom"]).buffer(0) for k, v in house.items()}
    S = {k: to_eq(v["geom"]).buffer(0) for k, v in senate.items()}
    rows = []
    for h, hg in H.items():
        for s, sg in S.items():
            if not hg.intersects(sg):
                continue
            a = hg.intersection(sg).area
            sh, ss = a / hg.area, a / sg.area
            if sh >= SLIVER or ss >= SLIVER:
                rows.append({"house_geo": h, "senate_geo": s,
                             "share_of_house": round(sh, 4), "share_of_senate": round(ss, 4)})
    return sorted(rows, key=lambda r: (r["house_geo"], -r["share_of_house"]))


def main() -> None:
    if "--fetch" in sys.argv:
        fetch()
    meta = {n: archive_meta(n) for n in LAYERS}
    house = load("house22", "house_id", "HD")
    senate = load("senate22", "senate_id", "SD")
    assert len(house) == 51 and len(senate) == 25, (len(house), len(senate))
    write_app_geojson(house, "sldl", "House")
    write_app_geojson(senate, "sldu", "Senate")
    rows = overlaps(house, senate)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    with (OUT_DATA / "district_overlap.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    counties = {**{k: v["county"] for k, v in house.items()}, **{k: v["county"] for k, v in senate.items()}}
    (OUT_DATA / "district_counties.json").write_text(json.dumps(counties, indent=1, sort_keys=True))
    (OUT_DATA / "boundaries_meta.json").write_text(json.dumps(meta, indent=1))
    missing = [h for h in house if not any(r["house_geo"] == h for r in rows)]
    print(f"{len(rows)} overlap pairs; house districts without a senate match: {missing or 'none'}")


if __name__ == "__main__":
    main()
