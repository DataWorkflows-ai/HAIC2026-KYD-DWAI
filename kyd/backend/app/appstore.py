"""Accounts, chats and dashboards (db/app.sql). Postgres when live mode is serving from Postgres, else a local
SQLite file (KYD_APP_DB). Both use the same tables; SQL is written with %s placeholders."""
from __future__ import annotations
import hashlib
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from functools import lru_cache

from .audit import _pg
from .config import settings

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
  pw_hash TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('owner','admin','user')),
  disabled INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, last_login TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS users_one_owner ON users (role) WHERE role = 'owner';
CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), title TEXT NOT NULL,
  pinned INTEGER NOT NULL DEFAULT 0, archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS chats_user ON chats (user_id, updated_at);
CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT NOT NULL REFERENCES chats(id),
  role TEXT NOT NULL CHECK (role IN ('user','assistant')), content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS messages_chat ON messages (chat_id, id);
CREATE TABLE IF NOT EXISTS dashboards (user_id TEXT PRIMARY KEY REFERENCES users(id), layout TEXT NOT NULL,
  updated_at TEXT NOT NULL);
"""
BOOLS = ("disabled", "pinned", "archived")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(8)}"


def _norm(row: dict) -> dict:
    return {k: bool(v) if k in BOOLS else v for k, v in row.items()}


class _Sqlite:
    backend = "sqlite"

    def __init__(self, path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._c = sqlite3.connect(path, check_same_thread=False)
        self._c.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._c.executescript(SQLITE_DDL)

    def q(self, sql: str, *args) -> list[dict]:
        sql = sql.replace("app.", "").replace("%s", "?")
        with self._lock:
            cur = self._c.execute(sql, args)
            rows = [_norm(dict(r)) for r in cur.fetchall()]
            self._c.commit()
            return rows


class _Postgres:
    backend = "postgres"

    def __init__(self, pool) -> None:
        self._pool = pool

    def q(self, sql: str, *args) -> list[dict]:
        with self._pool.connection() as conn, conn.cursor(binary=True) as cur:
            cur.execute(sql, args)
            return [_norm(r) for r in cur.fetchall()] if cur.description else []


fallback_reason: str | None = None


@lru_cache
def store():
    """Postgres when live mode serves from it and db/app.sql has been applied; otherwise the local SQLite file
    (on a host with an ephemeral disk, accounts then last until the next deploy; /api/health says so)."""
    global fallback_reason
    pg = _pg()
    if pg is not None:
        s = _Postgres(pg._pool)
        try:
            s.q("SELECT id FROM app.users LIMIT 1")
            return s
        except Exception as e:
            fallback_reason = f"app schema unavailable ({type(e).__name__}); run db/app.sql"
    return _Sqlite(settings().app_db)


def q(sql: str, *args) -> list[dict]:
    return store().q(sql, *args)


# ── users ─────────────────────────────────────────────────────────────────
USER_COLS = "id, email, name, role, disabled, created_at, last_login"


def credential_stamp(pw_hash: str) -> str:
    """A password change produces a different stamp. Tokens carry it; the hash itself stays in the database."""
    return hashlib.sha256(pw_hash.encode()).hexdigest()[:16]


def user_by_email(email: str) -> dict | None:
    rows = q("SELECT id, email, name, role, disabled, created_at, last_login, pw_hash FROM app.users WHERE email = %s",
             email.lower())
    if not rows:
        return None
    rows[0]["cred"] = credential_stamp(rows[0]["pw_hash"])
    return rows[0]


def user_by_id(uid: str) -> dict | None:
    rows = q(f"SELECT {USER_COLS}, pw_hash FROM app.users WHERE id = %s", uid)
    if not rows:
        return None
    u = rows[0]
    u["cred"] = credential_stamp(u.pop("pw_hash"))
    return u


def has_owner() -> bool:
    return bool(q("SELECT id FROM app.users WHERE role = 'owner'"))


def create_user(email: str, name: str, pw_hash: str, role: str) -> dict:
    uid = new_id("u")
    q("INSERT INTO app.users (id, email, name, pw_hash, role, disabled, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
      uid, email.lower(), name, pw_hash, role, False, now())
    return user_by_id(uid)


def touch_login(uid: str) -> None:
    q("UPDATE app.users SET last_login = %s WHERE id = %s", now(), uid)


def set_password(uid: str, pw_hash: str) -> None:
    q("UPDATE app.users SET pw_hash = %s WHERE id = %s", pw_hash, uid)


def list_users() -> list[dict]:
    return q(f"SELECT {USER_COLS} FROM app.users ORDER BY created_at")


def update_user(uid: str, role: str | None = None, disabled: bool | None = None) -> None:
    if role is not None:
        q("UPDATE app.users SET role = %s WHERE id = %s", role, uid)
    if disabled is not None:
        q("UPDATE app.users SET disabled = %s WHERE id = %s", disabled, uid)


# ── chats ─────────────────────────────────────────────────────────────────
CHAT_COLS = "id, title, pinned, archived, created_at, updated_at"


def list_chats(uid: str, archived: bool = False, search: str = "") -> list[dict]:
    sql = f"SELECT {CHAT_COLS} FROM app.chats WHERE user_id = %s AND archived = %s"
    args: list = [uid, archived]
    if search:
        like = f"%{search.lower()}%"
        sql += (" AND (lower(title) LIKE %s OR id IN (SELECT chat_id FROM app.messages WHERE lower(content) LIKE %s))")
        args += [like, like]
    return q(sql + " ORDER BY pinned DESC, updated_at DESC LIMIT 200", *args)


def get_chat(uid: str, cid: str) -> dict | None:
    rows = q(f"SELECT {CHAT_COLS} FROM app.chats WHERE id = %s AND user_id = %s", cid, uid)
    return rows[0] if rows else None


def create_chat(uid: str, title: str) -> dict:
    cid, t = new_id("c"), now()
    q("INSERT INTO app.chats (id, user_id, title, pinned, archived, created_at, updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
      cid, uid, title, False, False, t, t)
    return get_chat(uid, cid)


def update_chat(uid: str, cid: str, title: str | None = None, pinned: bool | None = None,
                archived: bool | None = None) -> None:
    for col, v in (("title", title), ("pinned", pinned), ("archived", archived)):
        if v is not None:
            q(f"UPDATE app.chats SET {col} = %s WHERE id = %s AND user_id = %s", v, cid, uid)


def messages(cid: str) -> list[dict]:
    out = []
    for m in q("SELECT id, role, content, created_at FROM app.messages WHERE chat_id = %s ORDER BY id", cid):
        out.append({**m, "content": json.loads(m["content"]) if m["role"] == "assistant" else m["content"]})
    return out


def add_message(cid: str, role: str, content) -> None:
    t = now()
    q("INSERT INTO app.messages (chat_id, role, content, created_at) VALUES (%s,%s,%s,%s)",
      cid, role, content if isinstance(content, str) else json.dumps(content, default=str), t)
    q("UPDATE app.chats SET updated_at = %s WHERE id = %s", t, cid)


def counts() -> dict:
    n = lambda t: q(f"SELECT count(*) AS n FROM app.{t}")[0]["n"]
    return {"users": n("users"), "chats": n("chats"), "messages": n("messages")}


# ── dashboards ────────────────────────────────────────────────────────────
def get_dashboard(uid: str) -> dict | None:
    rows = q("SELECT layout, updated_at FROM app.dashboards WHERE user_id = %s", uid)
    return {"layout": json.loads(rows[0]["layout"]), "updated_at": rows[0]["updated_at"]} if rows else None


def save_dashboard(uid: str, layout) -> str:
    t, body = now(), json.dumps(layout)
    if q("SELECT user_id FROM app.dashboards WHERE user_id = %s", uid):
        q("UPDATE app.dashboards SET layout = %s, updated_at = %s WHERE user_id = %s", body, t, uid)
    else:
        q("INSERT INTO app.dashboards (user_id, layout, updated_at) VALUES (%s,%s,%s)", uid, body, t)
    return t

