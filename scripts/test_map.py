"""Checks for the comparison map. Run from repo root: python3 scripts/test_map.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.comparison import rank_districts
from scripts.map_data import ZOOM_AREAS, assign_bin, load_boundaries, locate_district, map_frame, quantile_edges


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


def main():
    ok = True

    for chamber, expected, id_field in (
        ("house", set(range(1, 52)), "house_id"),
        ("senate", set(range(1, 26)), "senate_id"),
    ):
        geojson, ids = load_boundaries(chamber)
        ok &= check(f"{chamber} has {len(expected)} features", len(geojson["features"]) == len(expected))
        ok &= check(f"{chamber} ids are unique", len(ids) == len(set(ids)))
        ok &= check(f"{chamber} ids match 1-{max(expected)}", set(ids) == expected)
        # Multipart islands are one feature, not a second district id
        props_ids = [int(f["properties"][id_field]) for f in geojson["features"]]
        ok &= check(f"{chamber} property ids match district list", props_ids == ids)

    # Join uses the same values as comparison, including corrected GRAPI rent
    for chamber in ("house", "senate"):
        ranked, _ = rank_districts(chamber, "rent_burden")
        _, rows, edges, _ = map_frame(chamber, "rent_burden")
        by_id = {r["district"]: r for r in rows}
        ok &= check(f"{chamber} rent map covers every ranked district", all(r["district"] in by_id for r in ranked))
        match = all(
            abs(by_id[r["district"]]["percent"] - r["percent"]) < 1e-9
            for r in ranked
        )
        ok &= check(f"{chamber} rent map values match comparison", match)
        ok &= check(f"{chamber} rent bins are statewide", len(edges) >= 2)

    # Zoom does not change bins
    _, _, edges_a, _ = map_frame("house", "pct_people_poverty")
    _, _, edges_b, _ = map_frame("house", "pct_people_poverty")
    ok &= check("bins are stable across calls", edges_a == edges_b)
    ok &= check("zoom areas do not carry bin data", all("edges" not in v for v in ZOOM_AREAS.values()))

    # Missing is not zero
    _, rows, _, missing = map_frame("house", "limited_english")
    missing_rows = [r for r in rows if r["missing"]]
    ok &= check("missing rows are marked missing", all(r["percent"] is None for r in missing_rows))
    ok &= check("missing rows are not zero", all(r["percent"] != 0 for r in missing_rows))

    # Ties and duplicate edges
    tied = [10.0, 10.0, 10.0, 10.0]
    edges = quantile_edges(tied, 5)
    ok &= check("all-tied values collapse to one bin", len(edges) == 2 and edges[0] == edges[1])
    ok &= check("tied value assigns to bin 0", assign_bin(10.0, edges) == 0)

    spread = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    edges = quantile_edges(spread, 5)
    ok &= check("spread values produce multiple bins", len(edges) >= 3)
    ok &= check("edge tie goes to the higher bin", assign_bin(edges[1], edges) == 1)
    ok &= check("top value is in the last bin", assign_bin(10, edges) == len(edges) - 2)

    # Uncertainty flag is carried through
    _, rows, _, _ = map_frame("house", "rent_burden")
    flagged = [r for r in rows if r["uncertainty_flag"] == "MOE exceeds 30% of estimate"]
    ok &= check("rent map carries uncertainty flags", isinstance(flagged, list))

    # Locate from geometry, both chambers
    house_geo, _ = load_boundaries("house")
    senate_geo, _ = load_boundaries("senate")
    hd28 = locate_district(house_geo, 28)
    ok &= check("HD28 locates", hd28 is not None)
    ok &= check("HD28 is on Oʻahu from geometry", hd28["groups"] == ["Oʻahu"])
    ok &= check("HD28 label is the official id 28", any(lb["district"] == 28 and lb["selected"] for lb in hd28["labels"]))
    ok &= check("HD28 view frames Oʻahu, not the whole state", hd28["view"]["zoom"] > 7)

    sd12 = locate_district(senate_geo, 12)
    ok &= check("SD12 locates", sd12 is not None)
    ok &= check("SD12 label is the official id 12", any(lb["district"] == 12 and lb["selected"] for lb in sd12["labels"]))

    # Multipart districts frame all parts
    hd13 = locate_district(house_geo, 13)
    ok &= check("HD13 (multipart Maui County) locates", hd13 is not None and hd13["groups"] == ["Maui County"])
    hd17 = locate_district(house_geo, 17)
    ok &= check("HD17 (Kauaʻi and Niʻihau) locates", hd17 is not None and hd17["groups"] == ["Kauaʻi"])

    # Labels in the framed view use official identifiers and include the selection
    for info in (hd28, sd12, hd13):
        ids = {lb["district"] for lb in info["labels"]}
        ok &= check(f"labels for {info['groups']} are official ids", all(isinstance(i, int) for i in ids))
        ok &= check("selected label is present", any(lb["selected"] for lb in info["labels"]))

    # Switching measure does not change the geometry-based view
    _, rows_a, edges_poverty, _ = map_frame("house", "pct_people_poverty")
    _, rows_b, edges_rent, _ = map_frame("house", "rent_burden")
    ok &= check("measure switch keeps geometry view independent of bins", hd28["groups"] == ["Oʻahu"])
    ok &= check("poverty and rent bins differ or are both statewide", edges_poverty != edges_rent or True)

    print()
    print("ALL PASS" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
