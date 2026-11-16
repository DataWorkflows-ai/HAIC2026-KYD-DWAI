"""District rankings: every House or Senate district ranked on a few comparable measures.

Values come straight from the observation table (no new math), so each cell keeps its obs_id, MOE, method note
and quality flags and can be cited. Rank 1 = highest value. Districts with no value for a measure are unranked
for that measure (e.g. crime exists only for Oʻahu). Estimates are marked so the UI can label them.
"""
from __future__ import annotations

from .cache import cached
from .repo import repo

COLUMNS = [  # indicator, short label, kind (survey = ACS with MOE; estimate = modelled/allocated)
    ("pct_below_fpl", "Poverty rate", "survey"),
    ("pct_snap_gap", "SNAP gap (share of <200% FPL not reached)", "estimate"),
    ("laus_unemp_rate", "Unemployment 2025", "estimate"),
    ("pct_pop_lidac", "Residents in LIDAC areas", "estimate"),
    ("crime_violent_per_1k_est", "Violent crime per 1,000 (Oʻahu)", "estimate"),
]


@cached
def rankings(geo_type: str = "sldl") -> dict:
    r = repo()
    geos = r.geographies(geo_type)
    ids = [g.geo_id for g in geos]
    obs = {(o.geo_id, o.indicator): o for o in r.observations(ids, [c[0] for c in COLUMNS])}
    state = {o.indicator: o for o in r.observations(["HI"], [c[0] for c in COLUMNS])}
    ranks: dict[tuple[str, str], int] = {}
    for ind, _, _ in COLUMNS:
        vals = sorted(((obs[(g, ind)].value, g) for g in ids if (g, ind) in obs and obs[(g, ind)].value is not None),
                      reverse=True)
        for i, (_, g) in enumerate(vals, 1):
            ranks[(g, ind)] = i
    rows = [{"geo_id": g.geo_id, "name": g.name, "counties": g.counties,
             "cells": {ind: ({"obs": obs[(g.geo_id, ind)], "rank": ranks.get((g.geo_id, ind))}
                             if (g.geo_id, ind) in obs else None) for ind, _, _ in COLUMNS}} for g in geos]
    return {"geo_type": geo_type,
            "columns": [{"indicator": i, "label": l, "kind": k, "ranked": sum(1 for g in ids if (g, i) in ranks)}
                        for i, l, k in COLUMNS],
            "state": {i: state.get(i) for i, _, _ in COLUMNS}, "rows": rows,
            "notes": ["Rank 1 = highest value. Click any figure for its source, method and margin of error.",
                      "Poverty is an ACS 2020–2024 survey estimate with a 90% margin of error; districts whose "
                      "margins overlap may not truly differ in rank.",
                      "Columns marked ESTIMATE are modelled or allocated (SNAP gap: counts-based proxy; unemployment: "
                      "DBEDT county LAUS split by ACS shares; LIDAC: 2020 block-group population; crime: HPD beats "
                      "traced from report maps, Oʻahu only)."]}
