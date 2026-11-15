-- KYD schema. Postgres 16 + PostGIS + pgvector. Idempotent.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS facts;
CREATE SCHEMA IF NOT EXISTS programs;
CREATE SCHEMA IF NOT EXISTS vec;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS watchdog;

-- ── reference ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ref.geography (
  geo_id        text PRIMARY KEY,            -- HI, CNTY-15003, SD-01, HD-51
  geo_type      text NOT NULL CHECK (geo_type IN ('state','county','sldu','sldl','tract','zcta')),
  name          text NOT NULL,               -- display name with ʻokina/kahakō
  name_ascii    text NOT NULL,               -- normalized for matching
  census_geoid  text,                        -- e.g. 15001 for SLDU 001
  county_fips   text[],                      -- counties the district touches
  vintage       text NOT NULL,               -- boundary vintage, e.g. '2022'
  geom          geometry(MultiPolygon, 4326)
);
CREATE INDEX IF NOT EXISTS geography_geom_gix ON ref.geography USING gist (geom);

CREATE TABLE IF NOT EXISTS ref.place_alias (   -- gazetteer: neighborhoods/towns → districts
  alias_ascii text NOT NULL,
  geo_id      text NOT NULL REFERENCES ref.geography,
  share       numeric,                         -- population share of alias inside district
  PRIMARY KEY (alias_ascii, geo_id)
);

CREATE TABLE IF NOT EXISTS ref.source (
  source_id   text PRIMARY KEY,               -- acs5_2023, dotax_2023_county, ...
  publisher   text NOT NULL,
  title       text NOT NULL,
  url         text,
  license     text,
  release_date date,
  retrieved_at timestamptz,
  checksum    text
);

CREATE TABLE IF NOT EXISTS ref.indicator (
  indicator   text PRIMARY KEY,               -- median_hh_income
  label       text NOT NULL,
  unit        text NOT NULL,                  -- usd, pct, count, years
  topic       text NOT NULL,                  -- income, housing, age, ...
  acs_vars    text[],                         -- B19013_001E ...
  description text
);

-- ── facts: long observation table (§2.1) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS facts.observation (
  obs_id      bigserial PRIMARY KEY,
  geo_id      text NOT NULL REFERENCES ref.geography,
  indicator   text NOT NULL REFERENCES ref.indicator,
  vintage     text NOT NULL,                  -- '2019-2023'
  value       numeric,
  moe         numeric,
  cv          numeric GENERATED ALWAYS AS (CASE WHEN value IS NULL OR value = 0 OR moe IS NULL THEN NULL
                                              ELSE (moe / 1.645) / abs(value) END) STORED,
  universe    text,
  method      text NOT NULL DEFAULT 'direct' CHECK (method IN ('direct','apportioned','derived','modeled')),
  method_note text,
  source_id   text NOT NULL REFERENCES ref.source,
  status      text NOT NULL DEFAULT 'live' CHECK (status IN ('staged','live','held','superseded')),
  loaded_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (geo_id, indicator, vintage, source_id)
);
CREATE INDEX IF NOT EXISTS obs_geo_ind ON facts.observation (geo_id, indicator) WHERE status = 'live';

CREATE TABLE IF NOT EXISTS facts.crosswalk (       -- §2.4 tract→district population weights
  from_geo text NOT NULL, to_geo text NOT NULL, weight numeric NOT NULL,
  basis text NOT NULL DEFAULT 'pop2020_blocks', vintage text NOT NULL,
  PRIMARY KEY (from_geo, to_geo, vintage)
);

-- ── programs (§2.3, §7) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS programs.program (
  program_id  text PRIMARY KEY,               -- snap, wic, med_quest ...
  name        text NOT NULL,
  agency      text NOT NULL,
  level       text NOT NULL CHECK (level IN ('federal','state','county','nonprofit')),
  summary     text,
  official_url text NOT NULL,
  target_population text[],
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS programs.eligibility_rule (
  rule_id     bigserial PRIMARY KEY,
  program_id  text NOT NULL REFERENCES programs.program,
  kind        text NOT NULL,                  -- income_fpl_max, age_min, household_has_child ...
  threshold   numeric,
  proxy_indicator text REFERENCES ref.indicator,  -- ACS-based population proxy
  note        text,
  effective_from date, effective_to date
);

CREATE TABLE IF NOT EXISTS programs.activity_log (  -- aggregate only; <10 suppressed
  program_id text NOT NULL REFERENCES programs.program,
  geo_id     text NOT NULL REFERENCES ref.geography,
  period     text NOT NULL,
  metric     text NOT NULL CHECK (metric IN ('applications','approvals','denials','enrolled')),
  denial_reason text NOT NULL DEFAULT '',
  n          integer CHECK (n IS NULL OR n >= 10),
  suppressed boolean NOT NULL DEFAULT false,
  source_id  text REFERENCES ref.source,
  PRIMARY KEY (program_id, geo_id, period, metric, denial_reason),
  CHECK (suppressed = (n IS NULL))
);

-- ── vectors / hybrid search (§2.5, §4.1) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS vec.district_vector (
  geo_id   text PRIMARY KEY REFERENCES ref.geography,
  vintage  text NOT NULL,
  features jsonb NOT NULL,                    -- named, standardized features
  embedding vector(16) NOT NULL,              -- adjust dim to feature count
  peer_group int
);

CREATE TABLE IF NOT EXISTS vec.doc_chunk (
  chunk_id  bigserial PRIMARY KEY,
  doc_kind  text NOT NULL,                    -- program_page, methods, faq
  ref_id    text,                             -- program_id etc.
  source_id text REFERENCES ref.source,
  body      text NOT NULL,
  tsv       tsvector GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
  embedding vector(1024)
);
CREATE INDEX IF NOT EXISTS doc_chunk_tsv ON vec.doc_chunk USING gin (tsv);
CREATE INDEX IF NOT EXISTS doc_chunk_hnsw ON vec.doc_chunk USING hnsw (embedding vector_cosine_ops);

-- ── audit: append-only, hash-chained (§8.1–8.2) ──────────────────────────
CREATE TABLE IF NOT EXISTS audit.access_log (
  seq        bigserial PRIMARY KEY,
  ts         timestamptz NOT NULL DEFAULT now(),
  actor      text NOT NULL,
  role       text NOT NULL,
  action     text NOT NULL,                   -- tool / endpoint
  route      text,                            -- S1 | S2
  geo_ids    text[],
  tables     text[],
  row_count  integer,
  export     boolean NOT NULL DEFAULT false,
  query_scrubbed text,
  prev_hash  text NOT NULL,
  hash       text NOT NULL
);
CREATE OR REPLACE FUNCTION audit.deny_mutation() RETURNS trigger LANGUAGE plpgsql AS
$$ BEGIN RAISE EXCEPTION 'audit.access_log is append-only'; END $$;
DROP TRIGGER IF EXISTS access_log_no_update ON audit.access_log;
CREATE TRIGGER access_log_no_update BEFORE UPDATE OR DELETE ON audit.access_log
  FOR EACH ROW EXECUTE FUNCTION audit.deny_mutation();

-- ── watchdog (§6) ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchdog.source_check (
  check_id bigserial PRIMARY KEY, source_id text, url text NOT NULL,
  method text NOT NULL,                      -- census_vintage, etag, rss, arcgis_modified, text_hash
  last_seen text, checked_at timestamptz NOT NULL DEFAULT now(), changed boolean NOT NULL
);
CREATE TABLE IF NOT EXISTS watchdog.ingest_run (
  run_id bigserial PRIMARY KEY, source_id text, started_at timestamptz DEFAULT now(),
  stage text NOT NULL CHECK (stage IN ('fetched','validated','staged','promoted','held','failed')),
  checksum text, rows_in int, issues jsonb
);
CREATE TABLE IF NOT EXISTS watchdog.changelog (
  id bigserial PRIMARY KEY, ts timestamptz DEFAULT now(), source_id text, summary text NOT NULL, run_id bigint
);

-- ── roles (§5.2) ─────────────────────────────────────────────────────────
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_app') THEN CREATE ROLE kyd_app; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_etl') THEN CREATE ROLE kyd_etl; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_auditor') THEN CREATE ROLE kyd_auditor; END IF;
END $$;
GRANT USAGE ON SCHEMA ref, facts, programs, vec TO kyd_app;
GRANT SELECT ON ALL TABLES IN SCHEMA ref, facts, programs, vec TO kyd_app;
GRANT USAGE ON SCHEMA audit TO kyd_app, kyd_auditor;
GRANT INSERT ON audit.access_log TO kyd_app;
GRANT USAGE ON SEQUENCE audit.access_log_seq_seq TO kyd_app;
GRANT SELECT ON audit.access_log TO kyd_auditor;
GRANT USAGE, CREATE ON SCHEMA ref, facts, programs, vec, watchdog TO kyd_etl;
