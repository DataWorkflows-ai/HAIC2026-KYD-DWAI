"""Join saved legislative boundaries to comparison results.

Boundaries are read from data/boundaries/. They are not downloaded at runtime.
Comparison values come from scripts.comparison.rank_districts; this module does
not recompute them.
"""

import json
from pathlib import Path

from scripts.comparison import rank_districts

ROOT = Path(__file__).resolve().parent.parent
BOUNDARIES = ROOT / "data" / "boundaries"

# View only. Comparison bins are computed from all districts in the chamber
# and are not recomputed when the view changes.
ZOOM_AREAS = {
    "Statewide": {"center": {"lat": 20.6, "lon": -157.0}, "zoom": 6.2},
    "Hawaiʻi Island": {"center": {"lat": 19.6, "lon": -155.5}, "zoom": 7.4},
    "Maui County": {"center": {"lat": 20.9, "lon": -156.5}, "zoom": 7.6},
    "Oʻahu": {"center": {"lat": 21.45, "lon": -157.95}, "zoom": 9.2},
    "Kauaʻi": {"center": {"lat": 22.05, "lon": -159.5}, "zoom": 9.0},
}

# Geographic boxes for the main island groups. A district is assigned by where
# its polygon parts fall, not by a district-to-island lookup table.
ISLAND_GROUPS = {
    "Hawaiʻi Island": {"lon": (-156.25, -154.70), "lat": (18.85, 20.30)},
    "Maui County": {"lon": (-157.40, -155.90), "lat": (20.45, 21.30)},
    "Oʻahu": {"lon": (-158.40, -157.60), "lat": (21.20, 21.75)},
    "Kauaʻi": {"lon": (-160.30, -159.20), "lat": (21.80, 22.30)},
}

TEAL_BINS = ["#D6E8EC", "#9BC4CC", "#5A9AAB", "#2E7A8C", "#0B5563"]
MISSING_COLOR = "#D0D5DA"


def load_boundaries(chamber: str):
    """Return GeoJSON with a `district` property, and the list of district ids."""
    if chamber == "house":
        path = BOUNDARIES / "house_2022.geojson"
        id_field = "house_id"
    elif chamber == "senate":
        path = BOUNDARIES / "senate_2022.geojson"
        id_field = "senate_id"
    else:
        raise ValueError("chamber must be house or senate")
    data = json.loads(path.read_text())
    ids = []
    for feat in data["features"]:
        props = feat["properties"]
        did = int(props[id_field])
        props["district"] = did
        ids.append(did)
    return data, ids


def quantile_edges(values, n=5):
    """Up to n+1 unique edges. Duplicate edges from ties are dropped.

    A single distinct value returns one edge repeated, which is one bin.
    """
    if not values:
        return []
    vals = sorted(float(v) for v in values)
    if len(set(vals)) == 1:
        return [vals[0], vals[0]]
    edges = []
    for i in range(n + 1):
        pos = i / n * (len(vals) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(vals) - 1)
        frac = pos - lo
        edges.append(vals[lo] * (1 - frac) + vals[hi] * frac)
    unique = [edges[0]]
    for edge in edges[1:]:
        if edge > unique[-1] + 1e-9:
            unique.append(edge)
    if len(unique) < 2:
        unique = [min(vals), max(vals)]
    return unique


def assign_bin(value, edges):
    """Bin index for a value. An edge tie goes to the higher bin, except the top."""
    if value is None or not edges:
        return None
    last = len(edges) - 2
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == last:
            if lo <= value <= hi or (lo == hi and value == lo):
                return i
        elif lo <= value < hi:
            return i
    return None


def _rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def _centroid(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _bbox(rings):
    xs = [p[0] for ring in rings for p in ring]
    ys = [p[1] for ring in rings for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def island_group(lon, lat):
    for name, box in ISLAND_GROUPS.items():
        if box["lon"][0] <= lon <= box["lon"][1] and box["lat"][0] <= lat <= box["lat"][1]:
            return name
    return None


def _feature(geojson, district):
    for feat in geojson["features"]:
        if int(feat["properties"]["district"]) == int(district):
            return feat
    return None


def groups_for_feature(feat):
    """Island groups touched by this feature's actual polygon parts."""
    groups = set()
    for ring in _rings(feat["geometry"]):
        lon, lat = _centroid(ring)
        group = island_group(lon, lat)
        if group:
            groups.add(group)
    return groups


def view_for_bbox(minlon, minlat, maxlon, maxlat, pad=0.08):
    """Center and zoom that frame a bounding box. Does not change color bins."""
    minlon -= pad
    maxlon += pad
    minlat -= pad
    maxlat += pad
    span = max(maxlon - minlon, maxlat - minlat)
    if span > 3:
        zoom = 6.2
    elif span > 1.4:
        zoom = 7.3
    elif span > 0.8:
        zoom = 8.2
    elif span > 0.45:
        zoom = 9.0
    else:
        zoom = 10.0
    return {
        "center": {"lat": (minlat + maxlat) / 2, "lon": (minlon + maxlon) / 2},
        "zoom": zoom,
    }


def locate_district(geojson, district):
    """Frame the island group(s) containing this district, from its geometry.

    Returns view, group names, and label points for every district in those
    groups. A district with parts on more than one group frames all of them.
    Labels use the official boundary identifier.
    """
    feat = _feature(geojson, district)
    if feat is None:
        return None
    groups = groups_for_feature(feat)
    if not groups:
        rings = _rings(feat["geometry"])
        minlon, minlat, maxlon, maxlat = _bbox(rings)
        return {
            "view": view_for_bbox(minlon, minlat, maxlon, maxlat),
            "groups": [],
            "labels": [{"district": int(district), "lon": _centroid(max(rings, key=len))[0],
                        "lat": _centroid(max(rings, key=len))[1], "selected": True}],
        }

    rings = []
    labels = []
    for other in geojson["features"]:
        other_groups = groups_for_feature(other)
        if not other_groups & groups:
            continue
        other_rings = _rings(other["geometry"])
        rings.extend(other_rings)
        # Label at the centroid of the largest part that falls in the framed groups.
        in_view = [r for r in other_rings if island_group(*_centroid(r)) in groups]
        if not in_view:
            in_view = other_rings
        ring = max(in_view, key=len)
        lon, lat = _centroid(ring)
        labels.append({
            "district": int(other["properties"]["district"]),
            "lon": lon,
            "lat": lat,
            "selected": int(other["properties"]["district"]) == int(district),
        })

    minlon, minlat, maxlon, maxlat = _bbox(rings)
    return {
        "view": view_for_bbox(minlon, minlat, maxlon, maxlat),
        "groups": sorted(groups),
        "labels": _separate_labels(labels),
    }


def _separate_labels(labels, min_sep=0.035):
    """Drop or nudge labels that would sit on top of each other.

    The selected district is always kept. Others are kept when they can be
    placed without colliding.
    """
    selected = [lb for lb in labels if lb["selected"]]
    others = [lb for lb in labels if not lb["selected"]]
    placed = []
    for lb in selected + others:
        point = dict(lb)
        offsets = [(0, 0), (0.02, 0.015), (-0.02, 0.015), (0.02, -0.015), (-0.02, -0.015)]
        kept = False
        for dx, dy in offsets:
            candidate = (point["lon"] + dx, point["lat"] + dy)
            if all(
                abs(candidate[0] - p["lon"]) > min_sep or abs(candidate[1] - p["lat"]) > min_sep
                for p in placed
            ):
                point["lon"], point["lat"] = candidate
                placed.append(point)
                kept = True
                break
        if not kept and lb["selected"]:
            placed.append(point)
    return placed


def bin_label(edges, index):
    lo, hi = edges[index], edges[index + 1]
    if abs(hi - lo) < 1e-9:
        return f"{lo:.1f}%"
    return f"{lo:.1f}–{hi:.1f}%"


def map_frame(chamber: str, measure_key: str):
    """Join every boundary district to the comparison result.

    Missing estimates are marked missing and are never treated as zero.
    Returns geojson, rows, edges, missing_count.
    """
    geojson, ids = load_boundaries(chamber)
    ranked, missing_count = rank_districts(chamber, measure_key)
    by_district = {int(r["district"]): r for r in ranked}
    values = [r["percent"] for r in ranked if r["percent"] is not None]
    edges = quantile_edges(values, 5)

    rows = []
    for did in ids:
        row = by_district.get(did)
        if row is None:
            rows.append({
                "district": did,
                "percent": None,
                "percent_display": "No estimate",
                "percent_moe_display": "",
                "estimate": None,
                "estimate_moe": None,
                "denominator": "",
                "source_table": "",
                "year": "",
                "uncertainty_flag": "missing",
                "missing": True,
                "bin": None,
                "bin_label": "No estimate",
            })
            continue
        b = assign_bin(row["percent"], edges)
        rows.append({
            "district": did,
            "percent": row["percent"],
            "percent_display": row["percent_display"],
            "percent_moe_display": row["percent_moe_display"],
            "estimate": row["estimate"],
            "estimate_moe": row["estimate_moe"],
            "denominator": row["denominator"],
            "source_table": row["source_table"],
            "year": row["year"],
            "uncertainty_flag": row["uncertainty_flag"],
            "missing": False,
            "bin": b,
            "bin_label": bin_label(edges, b) if b is not None else "",
        })
    return geojson, rows, edges, missing_count
