"""Neighborhoods, neighborhood boards and county council districts for every legislative district.

Sources (all public ArcGIS services):
  Oʻahu neighborhoods   City & County of Honolulu, Realtor_Neighborhoods_2012 (Honolulu Board of Realtors areas)
  Oʻahu boards          City & County of Honolulu, Neighborhood_Boards_with_Dissolved_Subdistricts (2008 Neighborhood Plan)
  Council districts     Hawaiʻi Statewide GIS AdminBnd/MapServer 11 (Honolulu), 35 (Maui), 10 (Hawaiʻi).
                        Kauaʻi County Council is elected at large, so it has no districts.
  Neighbor-island places  Hawaiʻi Statewide GIS HistoricCultural/MapServer 2 (USGS GNIS, "Populated Place"),
                        which also supplies the ʻokina/kahakō spelling for Oʻahu neighborhood names.

  python kyd/etl/load_local_areas.py            # use cached data/raw/gis/local/* if present
  python kyd/etl/load_local_areas.py --fetch    # re-download first

Outputs
  kyd/data/district_local.json   {geo_id: {"neighborhoods": [name...], "boards": [...], "council": [...]}}
  kyd/data/neighborhood_aliases.json   extra gazetteer entries, merged by load_places.py

Shares are by AREA (equal-area projection), like district_overlap.csv. A neighborhood is listed for a
district when at least 15% of the neighborhood lies inside it; boards and council districts are listed
when they cover at least 5% of the legislative district.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_boundaries import OUT_DATA, RAW, REPO, load, to_eq  # noqa: E402

HNL = "https://services.arcgis.com/tNJpAOha4mODLkXz/arcgis/rest/services"
SOH = "https://geodata.hawaii.gov/arcgis/rest/services"
SOURCES = {
    "oahu_neighborhoods": f"{HNL}/Realtor_Neighborhoods_2012/FeatureServer/0",
    "oahu_boards": f"{HNL}/Neighborhood_Boards_with_Dissolved_Subdistricts/FeatureServer/0",
    "council_honolulu": f"{SOH}/AdminBnd/MapServer/11",
    "council_maui": f"{SOH}/AdminBnd/MapServer/35",
    "council_hawaii": f"{SOH}/AdminBnd/MapServer/10",
    "gnis_places": f"{SOH}/HistoricCultural/MapServer/2",
}
WHERE = {"gnis_places": "feature_class='Populated Place'"}
LOCAL = RAW / "local"
NEIGHBORHOOD_MIN = 0.15
AREA_MIN = 0.05
COUNCIL_NAME = {"council_honolulu": "Honolulu City Council", "council_maui": "Maui County Council (residency area)",
                "council_hawaii": "Hawaiʻi County Council"}
SKIP_HOOD = {"", " ", "Military", "Airport/Industrial", "Oahu Cc", "Sand Island", "City Hall", "Queens",
             "Holiday Mart", "Kuakini", "Dillingham", "Lakeside", "Kapiolani", "University"}


def normalize(s: str) -> str:
    s = s.replace("ʻ", "").replace("‘", "").replace("'", "")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower().strip()


def fetch() -> None:
    import urllib.parse
    LOCAL.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        q = urllib.parse.urlencode({"where": WHERE.get(name, "1=1"), "outFields": "*", "outSR": 4326, "f": "geojson"})
        with urllib.request.urlopen(f"{url}/query?{q}", timeout=180) as r:
            (LOCAL / f"{name}.geojson").write_bytes(r.read())
        p = LOCAL / f"{name}.geojson"
        (LOCAL / f"{name}.geojson.sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n")
        print("fetched", name)


def feats(name: str) -> list[dict]:
    return json.loads((LOCAL / f"{name}.geojson").read_text(encoding="utf-8"))["features"]


JUNK = re.compile(r"^(Reserve.*|.*Golf Course|Military.*|.*Industrial.*)$", re.I)
FIX = {"Waialae Nui Rdge": "Waialae Nui Ridge"}


def hood_base(n: str) -> str:
    """'Manoa-Upper', 'Manoa Area', 'Kalihi-Lower' → 'Manoa', 'Kalihi'."""
    n = re.sub(r"\s+Area$", "", n.strip())
    n = re.sub(r"-(Upper|Lower|Mauka|Makai)$", "", n)
    return {"Mccully": "McCully", "Kam Heights": "Kamehameha Heights", "Kapio/Kinau/Ward": "Kapiolani-Kinau-Ward",
            "Moanalua Gardens": "Moanalua Gardens", "Dmnd Head": "Diamond Head"}.get(n, n)


def main() -> None:
    if "--fetch" in sys.argv or not all((LOCAL / f"{n}.geojson").exists() for n in SOURCES):
        fetch()
    raw_d = {**load("house22", "house_id", "HD"), **load("senate22", "senate_id", "SD")}
    D = {k: to_eq(v["geom"]).buffer(0) for k, v in raw_d.items()}

    # Hawaiian spelling from GNIS, keyed by the plain spelling
    spell = {}
    for f in feats("gnis_places"):
        n = re.sub(r"\s*\(historical\)$", "", f["properties"]["feature_name"])
        spell.setdefault(normalize(n), n)

    def proper(n: str) -> str:
        return spell.get(normalize(n), n)

    out: dict[str, dict] = {g: {"neighborhoods": [], "boards": [], "council": []} for g in D}
    aliases: dict[str, dict] = {}

    # 1. Oʻahu neighborhoods (polygons, dissolved by base name)
    hoods = defaultdict(list)
    for f in feats("oahu_neighborhoods"):
        n = FIX.get((f["properties"].get("neighborho") or "").strip(), (f["properties"].get("neighborho") or "").strip())
        if n in SKIP_HOOD or JUNK.match(n) or not f.get("geometry"):
            continue
        hoods[proper(hood_base(n))].append(to_eq(shape(f["geometry"])).buffer(0))
    for name, polys in hoods.items():
        g = unary_union(polys)
        hits = {}
        for gid, dg in D.items():
            if g.intersects(dg):
                a = g.intersection(dg).area
                if a / g.area >= NEIGHBORHOOD_MIN:
                    hits[gid] = (a / g.area, a)
        for gid, (share, a) in hits.items():
            out[gid]["neighborhoods"].append((a, name))
        add_alias(aliases, name, "neighborhood", {ch: sorted(([gid, round(s, 3)] for gid, (s, _) in hits.items()
                                                             if gid.startswith(ch)), key=lambda x: -x[1])
                                                 for ch in ("HD", "SD")})

    # 2. Neighbor-island places (GNIS points). Oʻahu is covered by the polygons above.
    #    Ranked by 2020 Census population where the place is also a CDP, so towns come before hamlets.
    from shapely.geometry import Point
    cdps = [(normalize(f["properties"]["name20"]), f["properties"]["pop20"], to_eq(shape(f["geometry"])).buffer(500))
            for f in json.loads((RAW / "cdp20.geojson").read_text())["features"]] if (RAW / "cdp20.geojson").exists() else []

    def pop_at(name: str, pt) -> float:   # same name AND the point lies in (or within 500 m of) that CDP
        return float(next((p for n, p, g in cdps if n == normalize(name) and g.contains(pt)), 0))
    for f in feats("gnis_places"):
        p = f["properties"]
        if p["county_name"] == "Honolulu" or not f.get("geometry"):
            continue
        name = re.sub(r"\s*\(historical\)$", "", p["feature_name"])
        if "(historical)" in p["feature_name"]:
            continue
        pt = to_eq(Point(f["geometry"]["coordinates"]))
        hit = {gid for gid, dg in D.items() if dg.contains(pt)}
        for gid in hit:
            out[gid]["neighborhoods"].append((pop_at(name, pt), name))
        add_alias(aliases, name, "place", {ch: [[g, 1.0] for g in sorted(hit) if g.startswith(ch)] for ch in ("HD", "SD")})

    # 3. Neighborhood boards and council districts: what covers each legislative district
    def cover(layer: str, label) -> None:
        for f in feats(layer):
            if not f.get("geometry"):
                continue
            g = to_eq(shape(f["geometry"])).buffer(0)
            for gid, dg in D.items():
                if g.intersects(dg):
                    s = g.intersection(dg).area / dg.area
                    if s >= AREA_MIN:
                        yield_ = label(f["properties"])
                        yield_["share"] = round(s, 3)
                        out[gid]["boards" if layer == "oahu_boards" else "council"].append(yield_)

    cover("oahu_boards", lambda p: {"number": int(p["board_num"]), "name": proper(p["towns"].replace("Dmnd Head", "Diamond Head"))})
    for layer in ("council_honolulu", "council_maui", "council_hawaii"):
        cover(layer, lambda p, layer=layer: {"body": COUNCIL_NAME[layer], "number": _council_num(p),
                                              "name": p.get("district")})   # Maui residency-area name; others none

    for gid, v in out.items():
        if not v["council"] and raw_d[gid]["county"].lower().startswith("kauai"):
            v["council"] = [{"body": "Kauaʻi County Council", "number": None, "name": "elected at large", "share": 1.0}]
        seen, hoods_sorted = set(), []
        for _, n in sorted(v["neighborhoods"], key=lambda x: (-x[0], x[1])):
            if n not in seen:
                seen.add(n)
                hoods_sorted.append(n)
        v["neighborhoods"] = hoods_sorted
        v["boards"].sort(key=lambda x: -x["share"])
        v["council"].sort(key=lambda x: -x["share"])

    meta = {"sources": SOURCES, "method": f"area overlap; neighborhoods ≥ {NEIGHBORHOOD_MIN:.0%} inside the district, "
                                           f"boards/council ≥ {AREA_MIN:.0%} of the district; neighbor-island places are "
                                           f"GNIS points (not boundaries)"}
    (OUT_DATA / "district_local.json").write_text(json.dumps({**meta, "districts": dict(sorted(out.items()))},
                                                             indent=1, ensure_ascii=False))
    (OUT_DATA / "neighborhood_aliases.json").write_text(json.dumps({**meta, "aliases": dict(sorted(aliases.items()))},
                                                                   indent=1, ensure_ascii=False))
    empty = [g for g, v in out.items() if not v["neighborhoods"]]
    print(f"district_local.json: {len(out)} districts; without neighborhoods: {empty or 'none'}; "
          f"{len(aliases)} neighborhood aliases")


def _council_num(p: dict) -> int | None:
    for k in ("distnumber", "districtnumber"):
        if p.get(k) is not None:
            return int(p[k])
    m = re.search(r"\d+", p.get("distname") or p.get("shortname") or "")
    return int(m.group()) if m else None


def add_alias(aliases: dict, name: str, kind: str, d: dict) -> None:
    key = normalize(name)
    if not any(d.values()):
        return
    if key in aliases:
        aliases[key]["ambiguous"] = True
        for ch in d:
            merged = {g: s for g, s in aliases[key].get(ch, [])} | {g: s for g, s in d[ch]}
            aliases[key][ch] = sorted(([g, s] for g, s in merged.items()), key=lambda x: -x[1])
        return
    aliases[key] = {"name": name, "kind": kind, **d}


if __name__ == "__main__":
    main()
