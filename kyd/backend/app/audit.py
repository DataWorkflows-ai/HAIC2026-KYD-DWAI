"""Append-only, hash-chained access log (§8.1–8.2). In fixture mode it writes JSONL;
in live mode it writes audit.access_log, where a trigger blocks UPDATE and DELETE."""
from __future__ import annotations
import hashlib
import json
import threading
from datetime import datetime, timezone
from .config import ROOT, settings
from .privacy import scrub

_lock = threading.Lock()
_LOG = ROOT / "backend" / "var" / "access_log.jsonl"


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
    with _lock:
        prev = _last_hash() if settings().data_mode != "live" else _pg_last_hash()
        entry["prev_hash"] = prev
        entry["hash"] = hashlib.sha256((prev + json.dumps(entry, sort_keys=True)).encode()).hexdigest()
        if settings().data_mode == "live":
            _pg_insert(entry)
        else:
            _LOG.parent.mkdir(parents=True, exist_ok=True)
            with _LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def verify_chain() -> dict:
    prev, n = "GENESIS", 0
    if _LOG.exists():
        for line in _LOG.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            h = e.pop("hash")
            if e["prev_hash"] != prev or hashlib.sha256((prev + json.dumps(e, sort_keys=True)).encode()).hexdigest() != h:
                return {"ok": False, "broken_at": n}
            prev, n = h, n + 1
    return {"ok": True, "entries": n}


def _pg_last_hash() -> str:
    from .services.repo import repo
    rows = repo()._q("SELECT hash FROM audit.access_log ORDER BY seq DESC LIMIT 1")  # type: ignore[attr-defined]
    return rows[0]["hash"] if rows else "GENESIS"


def _pg_insert(e: dict) -> None:
    from .services.repo import repo
    repo()._q("""INSERT INTO audit.access_log (ts, actor, role, action, route, geo_ids, row_count, export,
                 query_scrubbed, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING seq""",
              e["ts"], e["actor"], e["role"], e["action"], e["route"], e["geo_ids"], e["row_count"],
              e["export"], e["query_scrubbed"], e["prev_hash"], e["hash"])
