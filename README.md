# Know Your District (HAIC 2026, Challenge 1)

**Live app:** https://know-your-district-zio4.onrender.com — no login, no setup.
Shareable links work, for example https://know-your-district-zio4.onrender.com/house-44/map

A nonpartisan, cited profile of every Hawaiʻi State House and Senate district (2022 plan) for legislators and staff:
who lives there, how they are doing, which assistance programs fit, and where people who look eligible are not being reached.
Every number on screen traces to a named source, vintage and method, with margins of error where the source publishes them.

**Contents:** [Try it](#try-it-in-two-minutes) · [Run it locally](#run-it-locally) · [AI tier](#turn-on-the-ai-tier-optional) ·
[Checks](#run-the-checks) · [Frontend](#change-the-frontend) · [Data](#rebuild-the-data) · [Deploy](#deploy) ·
[Settings](#settings) · [What the data covers](#what-the-data-covers) · [How it works](#how-it-works-and-why-it-is-safe-to-put-in-front-of-the-public) ·
[Layout](#repository-layout) · [Roadmap](#roadmap) · [License](#license)

## Try it in two minutes

Open the [live app](https://know-your-district-zio4.onrender.com) and follow the tabs left to right.

| Step | Where | What to do |
|---|---|---|
| 1 | **Find** (header search) | Type a district number, a legislator, a place, a neighborhood or a ZIP code. It lists every district that matches. |
| 2 | **Overview** | Pick a district. Read the headline figures beside the county and the state. Customize the indicator table (add, hide, drag to reorder), then Print or CSV. |
| 3 | **Map** | Pick an indicator. Each district shows its number and value; hover for value and rank. Toggle county council lines. |
| 4 | **Compare** | Choose any two districts, or a district and the state. Every row carries the Census significance test. |
| 5 | **Rankings** | All 51 House or 25 Senate districts on poverty, SNAP gap, unemployment, LIDAC share and violent crime (Oʻahu). Sort a column and the map above recolors. |
| 6 | **Programs** | SNAP uptake peers (districts with similar need that reach more people), 15 programs scored for fit, cross-program eligibility estimates, and the district's school, housing, health and safety context. |
| 7 | **Ask** | Click a suggested question or type your own, for example "Which programs fit HD 44?" or "Compare SD 12 with the state". Answers use only figures returned by tools and cite each one. |
| 8 | **Sources** | The 29-source library (also in [SOURCES.md](SOURCES.md)) and the build-time verification report. |

The app works on a phone, a tablet and a computer.

## Run it locally

You need **Python 3.12 or newer** and **git**. Nothing else: the database (`kyd/data/kyd.sqlite`) and the built
frontend (`kyd/frontend/dist`) are committed, so there is no database server and no build step.

**1. Get the code**

```bash
git clone https://github.com/DataWorkflows-ai/HAIC2026-KYD-DWAI.git
cd HAIC2026-KYD-DWAI
```

**2. Create a virtual environment and install the dependencies**

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r kyd/backend/requirements.txt
```

**3. Start the app**

```bash
cd kyd/backend
uvicorn app.main:app --port 8060
```

**4. Open http://localhost:8060**

You should see the Overview tab. To confirm the server is healthy, open http://localhost:8060/api/health; it returns
`"ok": true`, `"mode": "sqlite"` and `"geographies": 77`. The API reference is at http://localhost:8060/docs.

Out of the box the Ask tab answers with the rule-based tier (`"llm": "none"`). Every other tab is fully functional.

## Turn on the AI tier (optional)

The Ask tab can hand open-ended questions to a language model. The model only chooses which tool to call; it never
writes a number.

1. Copy the example settings file: `cp kyd/backend/.env.example kyd/backend/.env` (the `.env` file is git-ignored).
2. Edit `kyd/backend/.env`:

   ```
   KYD_LLM_PROVIDER=anthropic
   KYD_LLM_MODEL=<model id>
   KYD_LLM_API_KEY=<your key>
   ```

   For any OpenAI-compatible server, including a local one (llama.cpp, vLLM), use `KYD_LLM_PROVIDER=openai` and set
   `KYD_LLM_BASE_URL`, for example `http://127.0.0.1:8080/v1`.
3. Restart the app. `/api/health` now shows the provider under `"llm"`.

Never commit a key. On a host, set these three values in the host's environment settings.

## Run the checks

From `kyd/backend`, with the virtual environment active:

```bash
python -m pytest -q ../tests          # expect: 98 passed, 1 skipped
```

From the repository root:

```bash
python kyd/verify/run.py              # expect: 344 pass, 0 fail
```

The verifier re-reads the source PDFs, workbooks and Census extracts and compares them with the figures the app uses.
It rewrites `kyd/data/verification_report.json`; run `git checkout -- kyd/data/verification_report.json` afterwards
if you do not mean to commit a new report. A **fail** means a source changed format, a figure was mistyped or two
sources disagree. A **warn** is for review.

CI (`.github/workflows/kyd-ci.yml`) runs both, plus a real Neo4j load and the frontend build, on every pull request
that touches `kyd/`, `scripts/` or the source data.

## Change the frontend

Only needed if you edit files under `kyd/frontend/src`. Requires **Node 20 or newer**.

```bash
cd kyd/frontend
npm ci
npm run dev        # http://localhost:5173, proxies /api to the backend on port 8060
npm run build      # rebuilds kyd/frontend/dist; commit the result
```

Keep the backend from step 3 running in another terminal while you use `npm run dev`.

## Rebuild the data

Only needed if a source file changes. From the repository root:

```bash
python kyd/etl/load_acs_profile.py
```

This rebuilds `kyd/data/kyd.sqlite` and chains every other loader (state and county profiles, programs, HUD, school
meals, test scores, vital statistics, unemployment, LIDAC, HPD crime). Then run the checks above.
The source list lives in `kyd/data/sources.csv`; regenerate [SOURCES.md](SOURCES.md) with `python kyd/etl/make_sources_md.py`.

## Deploy

The public app runs on [Render](https://render.com) from [`render.yaml`](render.yaml) (a Render Blueprint).

1. In Render, choose **New → Blueprint** and connect this repository.
2. In the service's **Environment** settings, set `KYD_LLM_PROVIDER`, `KYD_LLM_MODEL` and `KYD_LLM_API_KEY` if you
   want the AI tier. Leave them empty for the rule-based tier.
3. Render builds with `pip install -r requirements.txt`, starts `uvicorn`, and checks `/api/health`.

The blueprint sets the instance type (`plan`). A free instance sleeps after 15 idle minutes; a paid one stays awake.
Any host that can run a Python web process works the same way: install `kyd/backend/requirements.txt`, then run
`uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `kyd/backend`.

## Settings

All settings are environment variables, or lines in `kyd/backend/.env`. The defaults run the app with no setup.

| Variable | Default | Meaning |
|---|---|---|
| `KYD_DATA_MODE` | `sqlite` | `sqlite` = the bundled database, read-only. `live` = Postgres and Neo4j. `fixture` = synthetic demo data for UI work. |
| `KYD_LLM_PROVIDER` | `none` | `none`, `anthropic`, or `openai` (any OpenAI-compatible server). |
| `KYD_LLM_MODEL`, `KYD_LLM_API_KEY`, `KYD_LLM_BASE_URL` | empty | Model id, key, and base URL for the AI tier. |
| `KYD_GRAPH_MODE` | `auto` | `auto` uses Neo4j if it is running, otherwise the in-memory graph. |
| `KYD_DATABASE_URL`, `KYD_NEO4J_URI`, `KYD_NEO4J_PASSWORD` | local dev values | Used only in `live` mode. Start both with `docker compose -f kyd/docker-compose.yml up -d`. |
| `KYD_AUTH_SECRET` | empty | HMAC key for signed role tokens. Empty means every visitor is an anonymous, read-only viewer. |

## What the data covers

- **Census ACS 2020–2024** district profiles (DP02–DP05, S1701 poverty ladder, S2201 SNAP, unemployment by sex, age, race and education)
- **SNAP gap**: people below 200% of poverty (Hawaiʻi's SNAP limit) not in SNAP households, by district (estimate)
- **Cross-program eligibility estimates**: free school meals, Lifeline, LIHEAP, WIC and Med-QUEST, each from one published rule
- **2025 unemployment** (DBEDT/LAUS, tract estimates rolled up to districts; county trend 2014–2025)
- **Low-income and disadvantaged communities (LIDAC 2026)** share of residents
- **HUD subsidized housing** (2025) and **HPHA public housing properties**
- **Free and reduced school meals** (SY2025-26) and **2025 Smarter Balanced / HSA Science** results (by school location; charter schools excluded)
- **Births and deaths 2000–2024** (estimate) and **HPD crime 2017–2025** for Oʻahu (estimate; beat lines traced from report maps)
- Island-level **Med-QUEST, TANF and SNAP** caseloads from the DHS Databook and BESSD

Estimates are labelled as estimates on screen, with the method and caveats beside them.
Program-by-program notes and the source files behind them are in [docs/DATA_NOTES.md](docs/DATA_NOTES.md).

## How it works (and why it is safe to put in front of the public)

- **Two tiers.** The numbers tier is plain code over a precomputed, read-only fact table — no AI writes or alters a number.
  The language tier only chooses which tool to call and with what arguments; it never writes SQL, and any number in its reply
  that cannot be traced to a tool result is removed before the answer is shown.
- **Read-only by design.** The public deployment opens the bundled SQLite database read-only; the Postgres mode uses a
  SELECT-only role. Every data and agent request is written to a hash-chained, append-only audit log
  (a local file here, a Postgres table in live mode), so tampering is detectable.
- **Population-level only.** No individual records, no address lookup; questions about individuals and partisan or electoral advice are refused.
- **Verified at build time.** Hand-entered report figures are re-checked against their PDFs and workbooks, Census variables against published totals,
  and independent sources against each other.

Architecture details: [kyd/ARCHITECTURE.md](kyd/ARCHITECTURE.md).

## Repository layout

| Path | What it holds |
|---|---|
| `kyd/backend/` | FastAPI app: API, the two-tier agent, audit log, auth |
| `kyd/frontend/` | React + TypeScript source (`src/`) and the committed build (`dist/`) |
| `kyd/data/` | The bundled database `kyd.sqlite`, program definitions, crosswalks, the source list |
| `kyd/etl/` | Loaders that rebuild the database from the source files |
| `kyd/verify/` | The build-time source verifier |
| `kyd/tests/` | Automated tests |
| `scripts/` | Program analyses (SNAP gap, TANF, GA, AABD, Med-QUEST) that the loaders import |
| `data/` | Source files (`raw/`), processed tables and boundaries |
| `docs/` | Challenge rules and [data notes](docs/DATA_NOTES.md) |
| `render.yaml` | Render Blueprint for the public deployment |
| `app.py` | The earlier Streamlit prototype, kept for reference |

## Roadmap

Designed and scoped, not in this release:

- **County council district profiles** (council lines are on the map today; full council-level figures are next)
- **Uptake peers beyond SNAP** (Med-QUEST, WIC, LIHEAP) once district-level enrollment is available, using the Neo4j program/population graph
- **Postgres (Neon) deployment** with the audit log and per-user activity history; local-model option for offices that cannot send data off-site
- Chat docked beside the profile; WIC clinic locations

## License

The code is released under the [MIT License](LICENSE). The data files keep the terms of their publishers: federal data is public
domain, and state, county and HIDOE figures are cited to their source (see [SOURCES.md](SOURCES.md) and
[data/raw/research/LICENSING.md](data/raw/research/LICENSING.md)). Nothing here implies endorsement by any agency.
