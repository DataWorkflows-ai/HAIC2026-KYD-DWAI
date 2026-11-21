"""Append-only, hash-chained access log (§8.1–8.2). With bundled data it writes JSONL; when live mode is
serving from Postgres it writes audit.access_log, where triggers block UPDATE, DELETE and TRUNCATE.

If a database write fails, the entry goes to the local JSONL file instead and /api/health reports
audit "degraded" (set KYD_AUDIT_STRICT=true to fail the request instead)."""
from __future__ import annotations
import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from .config import ROOT, settings
from .privacy import scrub

_lock = threading.Lock()
_LOG = ROOT / "backend" / "var" / "access_log.jsonl"
_db_failures = 0
_last_db_error: str | None = None


def _pg():
    """The Postgres repository when live mode is serving from Postgres, else None."""
    if settings().data_mode != "live":
        return None
    from .services.repo import repo
    r = repo()
    return r if getattr(r, "backend", "") == "postgres" else None


def status() -> dict:
    return {"store": "postgres" if _pg() is not None else "file", "degraded": _db_failures > 0,
            "db_write_failures": _db_failures, "last_error": _last_db_error}


def _last_hash() -> str:
    if not _LOG.exists():
        return "GENESIS"
    *_, last = _LOG.read_text(encoding="utf-8").splitlines() or ['{"hash":"GENESIS"}']
    return json.loads(last)["hash"]


def record(actor: str, role: str, action: str, *, route: str | None = None, geo_ids=None,
           row_count: int | None = None, export: bool = False, query: str | None = None) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "actor": actor, "role": role, "action": action,
             "route": route, "geo_ids": geo_ids or [], "row_count": row_count, "export": export,
             "query_scrubbed": scrub(query) if query else None}
    global _db_failures, _last_db_error
    with _lock:
        if _pg() is not None:
            try:
                _write(entry, _pg_last_hash(), _pg_insert)
                return
            except Exception as e:
                if settings().audit_strict:
                    raise
                _db_failures += 1
                _last_db_error = f"{type(e).__name__}: {str(e)[:200]}"
                entry.pop("prev_hash", None)
                entry.pop("hash", None)
        _write(entry, _last_hash(), _file_append)


def _write(entry: dict, prev: str, sink) -> None:
    entry["prev_hash"] = prev
    entry["hash"] = hashlib.sha256((prev + json.dumps(entry, sort_keys=True)).encode()).hexdigest()
    sink(entry)


def _file_append(entry: dict) -> None:
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def verify_chain() -> dict:
    """Recompute the chain. Checks the database log when live mode is serving from Postgres, else the file."""
    prev, n = "GENESIS", 0
    if _pg() is not None:
        cols = ("ts", "actor", "role", "action", "route", "geo_ids", "row_count", "export", "query_scrubbed", "prev_hash")
        for r in _pg()._q("SELECT seq, ts_text, actor, role, action, route, geo_ids, row_count, export, query_scrubbed, "
                          "prev_hash, hash FROM audit.access_log ORDER BY seq"):
            e = {k: (r["ts_text"] if k == "ts" else (r[k] or []) if k == "geo_ids" else r[k]) for k in cols}
            if e["prev_hash"] != prev or hashlib.sha256((prev + json.dumps(e, sort_keys=True)).encode()).hexdigest() != r["hash"]:
                return {"ok": False, "broken_at": n, "store": "postgres"}
            prev, n = r["hash"], n + 1
        return {"ok": True, "entries": n, "store": "postgres"}
    if _LOG.exists():
        for line in _LOG.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            h = e.pop("hash")
            if e["prev_hash"] != prev or hashlib.sha256((prev + json.dumps(e, sort_keys=True)).encode()).hexdigest() != h:
                return {"ok": False, "broken_at": n}
            prev, n = h, n + 1
    return {"ok": True, "entries": n}


def recent(days: int = 7, limit: int = 5000) -> list[dict]:
    """Newest-first entries from the last `days` days: ts, actor, role, action, route (no query text)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    keep = ("ts", "actor", "role", "action", "route")
    if _pg() is not None:
        rows = _pg()._q("SELECT ts_text AS ts, actor, role, action, route FROM audit.access_log WHERE ts >= %s::timestamptz "
                        "ORDER BY seq DESC LIMIT %s", since, limit)
        return [dict(r) for r in rows]
    if not _LOG.exists():
        return []
    out = []
    for line in reversed(_LOG.read_text(encoding="utf-8").splitlines()):
        e = json.loads(line)
        if e["ts"] < since or len(out) >= limit:
            break
        out.append({k: e.get(k) for k in keep})
    return out


def _pg_last_hash() -> str:
    rows = _pg()._q("SELECT hash FROM audit.access_log ORDER BY seq DESC LIMIT 1")
    return rows[0]["hash"] if rows else "GENESIS"


def _pg_insert(e: dict) -> None:
    # ts_text keeps the exact timestamp string that was hashed, so the chain can be recomputed later.
    _pg()._q("""INSERT INTO audit.access_log (ts, ts_text, actor, role, action, route, geo_ids, row_count, export,
                query_scrubbed, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING seq""",
             e["ts"], e["ts"], e["actor"], e["role"], e["action"], e["route"], e["geo_ids"], e["row_count"],
             e["export"], e["query_scrubbed"], e["prev_hash"], e["hash"])
