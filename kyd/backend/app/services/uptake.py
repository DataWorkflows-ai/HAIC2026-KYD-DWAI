"""SNAP uptake peers: districts with similar need that reach more of it.

Need = share of residents below 200% of poverty (Hawaiʻi's SNAP gross-income limit, ACS S1701).
Reach gap = share of those people who are not in SNAP households (pct_snap_gap, an ACS-based proxy).
Peers are districts in the same chamber whose need is within 3 points or 15% of this district's, and whose
gap is at least 2 points smaller. "At the peer's rate" = this district's people below 200% × the difference in gap.
Everything here is an estimate built from published counts, not administrative enrollment.
"""
from __future__ import annotations

from .cache import cached
from .repo import repo

IND = ["pct_below_200fpl", "pct_snap_gap", "pop_below_200fpl", "snap_gap_persons"]
NOTE = ("Estimate: need = share below 200% of poverty; reach gap = share of those people not in SNAP households "
        "(ACS 2020–2024 counts). Peers have need within 3 points or 15% and a gap at least 2 points smaller.")


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
    if not all(k in me and me[k].value is not None for k in ("pct_below_200fpl", "pct_snap_gap", "pop_below_200fpl")):
        return {"geo_id": geo_id, "peers": [], "note": "No SNAP reach estimate for this district."}
    need, gap, pop = me["pct_below_200fpl"].value, me["pct_snap_gap"].value, me["pop_below_200fpl"].value
    tol = max(3.0, 0.15 * need)
    peers = []
    for g in ids:
        o = obs.get(g, {})
        if g == geo_id or "pct_below_200fpl" not in o or "pct_snap_gap" not in o:
            continue
        n, gp = o["pct_below_200fpl"].value, o["pct_snap_gap"].value
        if n is None or gp is None or abs(n - need) > tol or gp > gap - 2:
            continue
        more = round(pop * (gap - gp) / 100)
        peers.append({"geo_id": g, "name": names[g], "need": o["pct_below_200fpl"], "gap": o["pct_snap_gap"],
                      "more_reached": {"obs_id": f"uptake-{geo_id}-{g}", "geo_id": geo_id, "indicator": "snap_more_reached_at_peer_rate",
                                       "label": f"More people in SNAP households if {geo_id} matched {g}'s reach (est.)",
                                       "value": float(more), "moe": None, "unit": "count", "vintage": "2020–2024",
                                       "method": "derived", "method_note": NOTE, "source_id": "acs5_2024_s2201_sld", "flags": ["estimate"]}})
    peers.sort(key=lambda p: p["gap"].value)
    return {"geo_id": geo_id, "name": names.get(geo_id, geo_id), "need": me["pct_below_200fpl"], "gap": me["pct_snap_gap"],
            "people_below_200fpl": me["pop_below_200fpl"], "not_reached": me.get("snap_gap_persons"),
            "peers": peers[:limit], "note": NOTE}
