"""SNAP uptake peers: districts with similar poverty-household need that reach more of it.

Uses the same strict ACS B22003 household measure as the Gaps tab:
poverty households receiving SNAP / poverty households. Peers with high uncertainty are excluded.
"""
from __future__ import annotations

from .cache import cached
from .repo import repo

IND = ["snap_poverty_hh_total", "snap_poverty_hh_receiving", "snap_strict_gap_households", "snap_poverty_hh_reach_rate"]
NOTE = ("Estimate: need = ACS poverty households; reach = poverty households reporting SNAP / poverty households "
        "(B22003, ACS 2020-2024). Peers with a reach MOE ratio above 30% are excluded. More reached is households.")


def _reliable(o) -> bool:
    return bool(o and o.value not in (None, 0) and (o.moe is None or abs(o.moe / o.value) <= 0.30))


@cached
def uptake_peers(geo_id: str, limit: int = 5) -> dict:
    r = repo()
    prefix = geo_id[:2]
    if prefix not in ("HD", "SD"):
        return {"geo_id": geo_id, "peers": [], "note": "Peers are found among House or Senate districts only."}
    ids = [g.geo_id for g in r.geographies("sldl" if prefix == "HD" else "sldu")]
    names = {g.geo_id: g.name for g in r.geographies("sldl" if prefix == "HD" else "sldu")}
    obs: dict[str, dict] = {}
    for o in r.observations(ids, IND):
        obs.setdefault(o.geo_id, {})[o.indicator] = o
    me = obs.get(geo_id, {})
    if not all(k in me and me[k].value is not None for k in ("snap_poverty_hh_total", "snap_poverty_hh_reach_rate")):
        return {"geo_id": geo_id, "peers": [], "note": "No SNAP poverty-household reach estimate for this district."}
    need, reach = me["snap_poverty_hh_total"].value, me["snap_poverty_hh_reach_rate"].value
    if not _reliable(me["snap_poverty_hh_reach_rate"]):
        return {"geo_id": geo_id, "peers": [], "note": "SNAP poverty-household reach is too uncertain for peer matching."}
    tol = max(100.0, 0.25 * need)
    peers = []
    for g in ids:
        o = obs.get(g, {})
        if g == geo_id or "snap_poverty_hh_total" not in o or "snap_poverty_hh_reach_rate" not in o:
            continue
        n, peer_reach = o["snap_poverty_hh_total"].value, o["snap_poverty_hh_reach_rate"].value
        if n is None or peer_reach is None or abs(n - need) > tol or peer_reach < reach + 2:
            continue
        if not _reliable(o["snap_poverty_hh_reach_rate"]):
            continue
        more = round(need * (peer_reach - reach) / 100)
        peers.append({"geo_id": g, "name": names[g], "need": o["snap_poverty_hh_total"], "gap": o["snap_poverty_hh_reach_rate"],
                      "more_reached": {"obs_id": f"uptake-{geo_id}-{g}", "geo_id": geo_id, "indicator": "snap_more_reached_at_peer_rate",
                                       "label": f"More poverty households reporting SNAP if {geo_id} matched {g}'s reach (est.)",
                                       "value": float(more), "moe": None, "unit": "count", "vintage": "2020–2024",
                                       "method": "derived", "method_note": NOTE, "source_id": "acs5_2024_b22003_sld", "flags": ["estimate"]}})
    peers.sort(key=lambda p: p["gap"].value, reverse=True)
    return {"geo_id": geo_id, "name": names.get(geo_id, geo_id), "need": me["snap_poverty_hh_total"], "gap": me["snap_poverty_hh_reach_rate"],
            "people_below_200fpl": None, "not_reached": me.get("snap_strict_gap_households"),
            "peers": peers[:limit], "note": NOTE}
