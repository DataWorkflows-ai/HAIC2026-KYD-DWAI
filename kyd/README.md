# Know Your District (HAIC 2026 Challenge 1)

Architecture and run instructions below. Tests: `cd backend && pytest ../tests`.

The HAIC 2026 Challenge 1 entry. The design decisions are in
`CLAUDE-haic-know-your-district-decisions.md`, and the section numbers in this
document refer to that file.

```
┌─────────────────────────── frontend/ (Vite + React + TS + Tailwind) ───────────────────────────┐
│ Header: brand · tabs · data-freshness chips                                                    │
│ Tabs: Overview · Map · Compare · Programs · Ask the Agent · Sources & Methods                  │
│ Every figure renders through <Figure>, which shows a "show the math" popover with the citation │
└───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                │ /api/*  (OpenAPI at /docs)
┌───────────────────────────────────── backend/app (FastAPI) ────────────────────────────────────┐
│ routers/   health · districts · programs · agent · sources                                     │
│ agent/     system1.py   gazetteer, guardrails, intent, fast-and-frugal tree → answer or escalate│
│            tools.py     get_district_profile · compare_district · find_programs ·              │
│                         estimate_eligible · get_map_layer · export_summary                     │
│            system2.py   LLM tool-calling (provider-agnostic); numbers come ONLY from tools      │
│ services/  repo.py      FactRepo  → PostgresRepo | FixtureRepo (numbers)                       │
│            graph.py     ProgramGraph → Neo4jGraph | FixtureGraph (relationships, lineage)      │
│            quality.py   CV>30% suppression, MOE handling, staleness flags (§9.2, §6.4)         │
│            anomaly.py   peer-district residual flags (§4)                                      │
│ audit/     hash-chained, append-only access log (§8.1–8.2)                                     │
│ privacy/   Presidio scrub (optional dependency, regex fallback) (§8.3)                         │
└───────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                │
                         ┌──────────────────────┴───────────────────────┐
                         ▼                                              ▼
┌──────── Postgres 16 + PostGIS + pgvector (db/schema.sql) ────────┐  ┌──── Neo4j 5 (db/neo4j/schema.cypher) ────┐
│  numbers, geometry, vectors, audit                               │  │ relationships + lineage only             │
│                                                                  │  │ Program→Agency, Program→Population,      │
│                                                                  │  │ Program→Rule→Indicator, Program↔Program, │
│                                                                  │  │ District→County, District↔Peer,          │
│                                                                  │  │ Indicator→SourceTable→Source, IngestRun  │
└──────────────────────────────────────────────────────────────────┘  └──────────────────────────────────────────┘
┌──────────────────────── Postgres detail ───────────────────────────────────────────────────────┐
│ ref.*       districts (geometry), geographies, sources, indicators                             │
│ facts.*     observation (long table: geo × indicator × vintage → value, moe, method, source)   │
│ programs.*  program, eligibility_rule (mapped to ACS variables), activity_log (suppressed <10)  │
│ vec.*       district_vector, doc_chunk (pgvector + FTS)                                        │
│ audit.*     access_log (hash chain), watchdog.*: source_check, ingest_run, changelog           │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
          ▲
          │ etl/ (DuckDB): load MANIFEST.csv files → validate → stage → promote (§6.2)
```

## Contracts

- **Observation.** Every number in the system is an `Observation` with fields
  `{id, geo_id, indicator, value, moe, cv, universe, vintage, source_id, method, flags}`.
  The API returns these objects as they are. The UI never computes figures itself.
- **Citation.** Each observation `id` resolves to a citation:
  `/api/sources/observation/{id}` returns the source, table, year, geography and method.
- **Agent answer.** An answer has the shape
  `{text, observations[], programs[], route: "S1"|"S2", escalation_reasons[], refused}`.
  Any number that appears in `text` must also appear in `observations` (§10.2 check).
- **Geography IDs** follow the pattern `HI`, `CNTY-15003`, `SD-01`…`SD-25` and
  `HD-01`…`HD-51`, for 77 standard geographies plus counties.

## Modes

- `KYD_DATA_MODE=fixture` is the default. The app reads `backend/fixtures/*.json`.
  These values are **synthetic demo data**, flagged `demo` in the data and shown
  with a DEMO banner in the UI. Fixture mode lets the UI and agent be developed
  while the real ETL lands.
- `KYD_DATA_MODE=live` reads numbers from Postgres (`KYD_DATABASE_URL`) and
  relationships from Neo4j (`KYD_NEO4J_URI`). `docker compose up` applies
  `db/schema.sql`. Then run `python etl/seed_graph.py` and the rest of `etl/`.

## Store split (supersedes decision doc §5.1 and §5.3)

- **Postgres** is the source of truth for every number: observations with MOE,
  geometry and crosswalks, embeddings for hybrid search, and the audit log.
- **Neo4j** holds relationships only. Graph nodes reference indicators and
  observations by ID and never store figures, so the citation rule has a single
  enforcement point in the fact table.

## Run (dev)

```bash
docker compose up -d db graph                 # Postgres(PostGIS, pgvector) + Neo4j
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8060     # API + serves frontend/dist
cd frontend && npm i && npm run dev           # :5173, proxies /api → :8060
```

## Next steps

1. Run `etl/load_acs.py` to build ACS SLDU/SLDL tables into `facts.observation`.
   The source list is in `Data/data/MANIFEST.csv`.
2. Write program JSON files with thresholds mapped to ACS variables
   (`programs/*.json`, 15–25 programs, §2.3).
3. Add the ArcGIS map adapter, keeping MapLibre as the fallback.
4. Wire System 2 to the chosen LLM. Run the golden set of 50 Q&A pairs
   (`tests/golden/`).
