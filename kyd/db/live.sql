-- Live mode (KYD_DATA_MODE=live): the app's data in Postgres / Supabase. Needs no extensions. Idempotent.
-- Loaded by kyd/etl/promote_to_postgres.py from kyd/data/kyd.sqlite and the run-time reference files.
-- The tables mirror kyd.sqlite column for column (same text obs_id), so both modes return the same answers.
CREATE SCHEMA IF NOT EXISTS kyd;
CREATE SCHEMA IF NOT EXISTS audit;

-- `ord` keeps the SQLite row order, so lists come back in the same order in both modes.
CREATE TABLE IF NOT EXISTS kyd.geography (
  ord integer NOT NULL, geo_id text PRIMARY KEY, geo_type text NOT NULL, name text NOT NULL, counties text NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS kyd.indicator (
  ord integer NOT NULL, indicator text PRIMARY KEY, label text, unit text, topic text, acs text
);
CREATE TABLE IF NOT EXISTS kyd.source (
  ord integer NOT NULL, source_id text PRIMARY KEY, publisher text, title text, url text, release_date text,
  license text, checksum text
);
CREATE TABLE IF NOT EXISTS kyd.observation (          -- geo_id also holds county ids that are not in kyd.geography
  ord integer NOT NULL, obs_id text PRIMARY KEY, geo_id text NOT NULL,
  indicator text NOT NULL REFERENCES kyd.indicator, value double precision, moe double precision, vintage text,
  method text, method_note text, source_id text NOT NULL REFERENCES kyd.source
);
CREATE INDEX IF NOT EXISTS observation_geo_ind ON kyd.observation (geo_id, indicator);
CREATE TABLE IF NOT EXISTS kyd.breakdown (
  ord integer NOT NULL, obs_id text PRIMARY KEY, geo_id text NOT NULL, topic text, dimension text, grp text, sex text,
  value double precision, moe double precision, numerator double precision, numerator_moe double precision,
  denominator double precision, denominator_moe double precision, quality_flag text, source_table text,
  universe text, notes text, vintage text, source_id text REFERENCES kyd.source
);
CREATE INDEX IF NOT EXISTS breakdown_geo_topic ON kyd.breakdown (geo_id, topic);

-- Reference files the app reads at run time (legislators, place names, programs, verification report, ...),
-- stored whole with a checksum, plus two documents precomputed from scripts/ (see promote_to_postgres.py).
CREATE TABLE IF NOT EXISTS kyd.datafile (
  name text PRIMARY KEY, content text NOT NULL, sha256 text NOT NULL, bytes integer NOT NULL,
  origin text NOT NULL,                      -- repo path, or 'computed: ...'
  loaded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS kyd.load_run (
  run_id bigserial PRIMARY KEY, loaded_at timestamptz NOT NULL DEFAULT now(), git_sha text, sqlite_sha256 text NOT NULL,
  counts jsonb NOT NULL
);

-- ── audit: append-only, hash-chained (§8.1–8.2) ──────────────────────────
CREATE TABLE IF NOT EXISTS audit.access_log (
  seq        bigserial PRIMARY KEY,
  ts         timestamptz NOT NULL DEFAULT now(),
  ts_text    text,                            -- the timestamp string that was hashed (chain verification)
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

-- ── roles: the app reads data and appends to the audit log; nothing else ──
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_app') THEN CREATE ROLE kyd_app; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_auditor') THEN CREATE ROLE kyd_auditor; END IF;
END $$;
GRANT USAGE ON SCHEMA kyd TO kyd_app;
GRANT SELECT ON ALL TABLES IN SCHEMA kyd TO kyd_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA kyd GRANT SELECT ON TABLES TO kyd_app;
GRANT USAGE ON SCHEMA audit TO kyd_app, kyd_auditor;
GRANT INSERT, SELECT ON audit.access_log TO kyd_app;
GRANT USAGE ON SEQUENCE audit.access_log_seq_seq TO kyd_app;
GRANT SELECT ON audit.access_log TO kyd_auditor;
