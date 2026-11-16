# Know Your District (KYD): Architecture

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

## Identity and roles

`app/auth.py`. Client-sent `x-kyd-*` headers are ignored unless `KYD_TRUST_PROXY_HEADERS=true`, which
is only safe behind an SSO proxy that strips them from incoming requests. Otherwise identity comes from an
HMAC-signed bearer token (`KYD_AUTH_SECRET`; mint with `python -m app.auth --sub NAME --role ROLE`).
No token = anonymous `viewer`. Roles: viewer, staff, legislator, auditor, admin. `/api/me` echoes the caller.
The frontend sends `sessionStorage.kyd_token` as the bearer token when present.

## Agent routing notes

- Guardrails refuse electoral advice and party politics, not voting records ("how did HD 22 vote on SB 123").
- District numbers are State Legislature numbers (verified against the official state GIS service for all 76).
  County council and Oʻahu neighborhood board numbers differ and are shown separately in the map cards.
- Place names, Oʻahu neighborhoods and ZIPs resolve through `kyd/data/place_aliases.json`. A place maps to one district only when
  that district holds ≥ 60% of its area; otherwise the agent escalates (`place_spans_districts`) and, with no
  LLM, asks which district.
- If System 2 fails (timeout, HTTP error, bad response), the request falls back to a System 1 template
  (`s2_error`) instead of returning a 500.
- Numbers in an S2 answer that do not match a returned observation are replaced in the text
  (`unsupported_numbers_removed`); they never reach the user.

## Knowledge graph (Neo4j)

`app/services/graph_data.py` builds one graph document from the committed data files: districts, counties,
House↔Senate overlaps, peer districts, legislators, neighborhoods, neighborhood boards, council districts,
programs, indicator lineage, and the datasets behind each program capability with their verification status.
Two backends answer from that same document:

- **Neo4j** (`KYD_GRAPH_MODE=neo4j`, or `auto` when Neo4j is reachable). Load it with
  `docker compose -f kyd/docker-compose.yml up -d graph` then `python kyd/etl/build_graph.py`.
  The loader stamps every node with a build id, prunes leftovers from earlier builds, then reads the graph back:
  node and relationship counts must equal the document, and `district_context()` must equal the in-memory answer
  for all 76 districts. Any mismatch exits non-zero.
- **In memory** (`KYD_GRAPH_MODE=fixture`, or `auto` when Neo4j is not running), so the app still runs with
  no database.

API: `/api/districts/{id}/context`, `/api/connections?a=&b=`, `/api/verification`. Agent tool:
`district_connections` (relationships only, worded without numbers so the figure check stays strict).

## Source verification

`python kyd/verify/run.py` checks every source behind Crystal's program scripts and writes
`kyd/data/verification_report.json` (shown in Sources & Methods and loaded into the graph).

| Source | What is checked |
|---|---|
| Census API extracts (`data/raw/*_districts.json`) | table and vintage, one row per district, every used variable present and numeric; **identities that pin each variable's meaning**: percent = count / total, subject-table rate = Data Profile rate, poverty-threshold ladder ordered, DP values = DBEDT workbook values, House sum = Senate sum |
| DHS Databook 2025 PDF | each table's heading is on the page the code cites; every hand-typed figure in `scripts/*.py` and `data/processed/*databook*` is re-read from the PDF; distributions add to 100; islands add to statewide |
| BESSD SFY 2026 workbook (`.numbers`) | blocks and header row found by name; the processed CSV equals the workbook cell by cell; columns add to TOTAL; Maui + Molokaʻi + Lānaʻi = Maui Branch; branches add to STATE |
| Cross-source | DHS testimony vs BESSD (same month); Databook vs BESSD caseloads; ACS poverty ladder and county rates vs Databook; ACS vs administrative SNAP (info) |

Status: **fail** = format change, transcription error or internal inconsistency (exit 1, CI fails);
**warn** = for review; **info** = shown, not judged. `--accept` records file hashes in `kyd/verify/manifest.json`
after review, so a replaced source file shows up as changed on the next run. `kyd/tests/test_verification.py`
corrupts copies of each source (swapped Census columns, a page inserted into the Databook, a typo in code, an
edited CSV cell) and asserts each one fails.

CI (`.github/workflows/kyd-ci.yml`) runs the verification, the tests, a real Neo4j load with read-back, and the
frontend build on every push and pull request that touches `kyd/`, `scripts/` or the source data.

## Modes

- **`KYD_DATA_MODE=sqlite`** is the default. It reads `kyd/data/kyd.sqlite`, which holds real ACS
  2020–2024 data for all 76 districts plus derived state totals. The file is committed to the repo,
  so the app needs no database server, and judges can run it as-is.
- `KYD_DATA_MODE=fixture` uses synthetic demo data and shows a DEMO banner. It is for UI work only.
- `KYD_DATA_MODE=live` reads numbers from Postgres (`KYD_DATABASE_URL`) and relationships from
  Neo4j (`KYD_NEO4J_URI`). This is the hosted, production version of the stack.

## Data build (run from repo root; outputs are committed)

| Script | Input | Output |
|---|---|---|
| `kyd/etl/load_boundaries.py [--fetch]` | State GIS AdminBnd/MapServer 33 and 34 | `data/raw/gis/*`, `kyd/frontend/public/geo/*.geojson`, `kyd/data/district_overlap.csv`, `district_counties.json` |
| `kyd/etl/load_acs_profile.py` | `data/raw/acs2024_5yr_{house,senate}_hi.xlsx` (DP02–DP05) | `kyd/data/kyd.sqlite` (28 indicators × 76 districts, plus derived state values) |
| `kyd/etl/load_local_areas.py [--fetch]` | Honolulu open data (Realtor neighborhoods, Neighborhood Boards), state GIS council districts and GNIS places | `kyd/data/district_local.json` (neighborhoods, boards, council per district), `neighborhood_aliases.json` |
| `kyd/etl/load_places.py [--fetch]` | State GIS Census/MapServer 28 (2020 CDPs) and 32 (ZCTAs) | `kyd/data/place_aliases.json` (place/ZIP → districts with area share) |
| `kyd/data/legislators.csv` | hand-curated, with a source on every row | Representation API |
| `kyd/data/programs.json` | hand-curated | Program graph (fixture form of the Neo4j model) |

The test `test_acs_matches_teammate_database` cross-checks the ACS loader against
`data/districts.db`, which `scripts/process_acs.py` builds independently.

## Map (frontend/src/MapTab.tsx)

- ArcGIS Maps SDK for JavaScript 4.33, loaded from the Esri CDN.
- **Official boundaries:** a live FeatureLayer from the Hawaiʻi Statewide GIS Program, drawn as white lines.
- **Choropleth:** a GeoJSONLayer from the bundled boundaries, joined to the selected indicator and shaded by quintile.
- **Basemap:** Esri World Imagery, which needs no key, or OpenStreetMap. Set `VITE_ARCGIS_API_KEY` to use Esri's vector basemaps instead.
- **Interaction:** on a computer, hover highlights a district and shows its Representative, the overlapping Senator(s) with share, key figures and top program. Click pins the district; double-click opens its profile. On touch devices, tap does the same.
- **Controls:** a House/Senate toggle carries the selection over to the largest overlapping district in the other chamber. Island quick-zoom buttons cover each island group.
- **"My office":** the star button next to the district picker sets the user's own district. The map chamber and selection default to it.
- **Party is intentionally not shown.**

## Known gaps

- **Legislator roster (as of 2026-11-13):**
  - 45 seats come from Office of Elections FINAL county reports or the Legislature roster.
  - 25 unopposed seats come from secondary sources and still need confirming against the primary report.
  - HD-24, 25, 28 and 37 are pending.
  - SD-23 and HD-43 are flagged for review.
- **Overlap shares** are by land area. Replace with 2020-block population weights (§2.4).
- **County comparisons are missing,** and so are state values for medians and poverty rates. Fix by allowlisting `api.census.gov` and loading the state and county ACS profiles.
- **Program ranking** compares against the state value where one exists, otherwise against the median district. The signal is weak for districts near the median.

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
