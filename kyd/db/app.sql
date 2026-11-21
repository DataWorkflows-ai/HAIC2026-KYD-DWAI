-- App accounts, chat history and dashboards (app/appstore.py). Idempotent and never dropped: the data reload
-- (promote_to_postgres.py) only replaces kyd.*, so accounts survive it. Timestamps are ISO-8601 UTC text so the
-- bundled SQLite store has the same columns.
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.users (
  id         text PRIMARY KEY,
  email      text NOT NULL UNIQUE,              -- lower-cased
  name       text NOT NULL,
  pw_hash    text NOT NULL,                     -- scrypt$n$r$p$salt$hash
  role       text NOT NULL CHECK (role IN ('owner', 'admin', 'user')),
  disabled   boolean NOT NULL DEFAULT false,
  created_at text NOT NULL,
  last_login text
);
CREATE UNIQUE INDEX IF NOT EXISTS users_one_owner ON app.users (role) WHERE role = 'owner';

CREATE TABLE IF NOT EXISTS app.chats (
  id         text PRIMARY KEY,
  user_id    text NOT NULL REFERENCES app.users(id),
  title      text NOT NULL,
  pinned     boolean NOT NULL DEFAULT false,
  archived   boolean NOT NULL DEFAULT false,
  created_at text NOT NULL,
  updated_at text NOT NULL
);
CREATE INDEX IF NOT EXISTS chats_user ON app.chats (user_id, updated_at);

CREATE TABLE IF NOT EXISTS app.messages (
  id         bigserial PRIMARY KEY,
  chat_id    text NOT NULL REFERENCES app.chats(id),
  role       text NOT NULL CHECK (role IN ('user', 'assistant')),
  content    text NOT NULL,                     -- question text, or the AgentAnswer as JSON
  created_at text NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_chat ON app.messages (chat_id, id);

CREATE TABLE IF NOT EXISTS app.dashboards (
  user_id    text PRIMARY KEY REFERENCES app.users(id),
  layout     text NOT NULL,                     -- JSON
  updated_at text NOT NULL
);

-- The app may read and write its own tables. It still cannot change kyd.* or the audit log. No DELETE:
-- chats are archived, accounts are disabled.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kyd_app') THEN CREATE ROLE kyd_app; END IF;
END $$;
GRANT USAGE ON SCHEMA app TO kyd_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA app TO kyd_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO kyd_app;
