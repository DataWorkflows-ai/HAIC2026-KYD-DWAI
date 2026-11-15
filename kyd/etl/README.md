# ETL

Pipeline: detect → fetch and archive → validate → stage → promote or hold → recompute → changelog
(decision doc §6.2). DuckDB handles in-process transforms. Results are written to Postgres
`facts.observation` with `status='staged'` and promoted to `'live'` after the checks pass.

| Script | Status | Target |
|---|---|---|
| `seed_graph.py` | done | Neo4j: programs, agencies, populations, rules, indicators |
| `load_acs.py` | TODO | Census API, ACS5 `state legislative district (upper|lower)`, HI = 15 → facts.observation |
| `load_boundaries.py` | TODO | 2022 SLDU/SLDL TIGER shapes → ref.geography.geom |
| `build_crosswalk.py` | TODO | 2020 blocks → tract × district weights → facts.crosswalk (§2.4) |
| `load_manifest.py` | TODO | `data/MANIFEST.csv` (repo root) files, routed by source |
| `watchdog.py` | TODO | change detection per source (§6.1) |
