"""Place-name and ZIP gazetteer → which legislative districts cover each place.

Source: Hawaii Statewide GIS Program, Census/MapServer
  layer 28 = 2020 Census Designated Places, layer 32 = 2020 ZIP Code Tabulation Areas.

  python kyd/etl/load_places.py            # use data/raw/gis/{cdp20,zcta20}.geojson if present
  python kyd/etl/load_places.py --fetch    # re-download first

Output
  kyd/data/place_aliases.json   {alias: {"name", "kind", "HD": [[geo_id, share], ...], "SD": [...]}}
                                also merges kyd/data/neighborhood_aliases.json (run load_local_areas.py first)

`share` is the fraction of the place's AREA inside the district (equal-area projection),
so it has the same population-weighting caveat as district_overlap.csv. Shares under 5%
are dropped as digitizing slivers. Aliases are normalized like system1.normalize
(no ʻokina or kahakō, lowercase), so "Kāneʻohe" and "Kaneohe" both match.
"""
from __future__ import annotations
import hashlib
import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_boundaries import RAW, OUT_DATA, REPO, load, to_eq  # noqa: E402

SERVICE = "https://geodata.hawaii.gov/arcgis/rest/services/Census/MapServer"
LAYERS = {"cdp20": 28, "zcta20": 32}
MIN_SHARE = 0.05
# Common short forms → CDP names. Hyphenated CDPs ("Haiku-Pauwela") also get each part as an alias.
EXTRA = {"honolulu": ["Urban Honolulu"], "mililani": ["Mililani Town", "Mililani Mauka"],
         "ewa": ["Ewa Beach", "Ewa Gentry", "Ewa Villages"]}


ENGLISH = {"triangle", "anchorage", "beachside", "hillcrest", "sisal", "marconi", "lakeside", "university",
           "downtown", "kokomo", "reserve", "military", "queens", "triangle park", "village park", "sunset beach"}


def normalize(s: str) -> str:
    s = s.replace("ʻ", "").replace("‘", "").replace("'", "")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower().strip()


def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, layer in LAYERS.items():
        url = f"{SERVICE}/{layer}/query?outFields=*&where=1%3D1&outSR=4326&f=geojson"
        with urllib.request.urlopen(url, timeout=180) as r:
            (RAW / f"{name}.geojson").write_bytes(r.read())
        p = RAW / f"{name}.geojson"
        (RAW / f"{name}.geojson.sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n")
        print("fetched", name)


def districts_for(geom, chambers: dict[str, dict]) -> dict[str, list]:
    g = to_eq(geom).buffer(0)
    out = {}
    for ch, polys in chambers.items():
        hits = []
        for gid, dg in polys.items():
            if g.intersects(dg):
                share = g.intersection(dg).area / g.area
                if share >= MIN_SHARE:
                    hits.append([gid, round(share, 3)])
        out[ch] = sorted(hits, key=lambda x: -x[1])
    return out


def main() -> None:
    if "--fetch" in sys.argv or not all((RAW / f"{n}.geojson").exists() for n in LAYERS):
        fetch()
    chambers = {"HD": {k: to_eq(v["geom"]).buffer(0) for k, v in load("house22", "house_id", "HD").items()},
                "SD": {k: to_eq(v["geom"]).buffer(0) for k, v in load("senate22", "senate_id", "SD").items()}}
    aliases: dict[str, dict] = {}

    def add(key: str, name: str, kind: str, d: dict) -> None:
        if not any(d.values()):
            return
        if key in aliases:                     # same name, two places (e.g. Kailua, Oʻahu and Kailua, Hawaiʻi)
            for ch in d:
                merged = {g: s for g, s in aliases[key][ch]} | {g: s for g, s in d[ch]}
                aliases[key][ch] = sorted(([g, s] for g, s in merged.items()), key=lambda x: -x[1])
            aliases[key]["ambiguous"] = True
            return
        aliases[key] = {"name": name, "kind": kind, **d}

    by_name = {}
    for f in json.loads((RAW / "cdp20.geojson").read_text())["features"]:
        p = f["properties"]
        d = districts_for(shape(f["geometry"]), chambers)
        by_name[p["name20"]] = d
        add(normalize(p["name20"]), p["name20"], "place", d)
    for short, fulls in EXTRA.items():
        for full in fulls:
            if full in by_name:
                add(short, full if len(fulls) == 1 else short.title(), "place", by_name[full])
        if len(fulls) > 1 and short in aliases:
            aliases[short]["ambiguous"] = True     # several places: always ask which one
    for full, d in by_name.items():
        for part in full.split("-") if "-" in full else []:
            if normalize(part) not in aliases:
                add(normalize(part), full, "place", d)
    for f in json.loads((RAW / "zcta20.geojson").read_text())["features"]:
        z = f["properties"]["zcta5ce20"]
        add(z, f"ZIP {z}", "zip", districts_for(shape(f["geometry"]), chambers))

    # Neighborhoods (Oʻahu) and GNIS places (neighbor islands) from load_local_areas.py fill in names that
    # are not Census places. Census places win on a name clash. Plain English words are left out so
    # that, say, "triangle" or "anchorage" in a question is not read as a place.
    extra = OUT_DATA / "neighborhood_aliases.json"
    if extra.exists():
        for k, v in json.loads(extra.read_text(encoding="utf-8"))["aliases"].items():
            if k not in aliases and k not in ENGLISH:
                aliases[k] = v
    else:
        print("note: run load_local_areas.py first to include neighborhoods")

    out = OUT_DATA / "place_aliases.json"
    out.write_text(json.dumps({"source": {k: f"{SERVICE}/{v}" for k, v in LAYERS.items()},
                               "method": f"area share of place inside district, slivers < {MIN_SHARE:.0%} dropped",
                               "aliases": dict(sorted(aliases.items()))}, indent=1, ensure_ascii=False))
    print(f"{out.relative_to(REPO)}: {len(aliases)} aliases")


if __name__ == "__main__":
    main()
