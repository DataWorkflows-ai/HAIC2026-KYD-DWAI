"""Small in-process cache for derived results (program ranking, peers, medians, map summary, cross-program).

The bundled SQLite and fixture data never change while the process runs, so entries never expire there.
In live (Postgres) mode facts can be promoted by an ETL run, so entries expire after `cache_ttl_seconds`.
`clear()` drops everything (call it after loading new data in-process).
"""
from __future__ import annotations
import functools
import threading
import time

from ..config import settings

_lock = threading.Lock()
_store: dict[tuple, tuple[float, object]] = {}


def _ttl() -> float | None:
    s = settings()
    return s.cache_ttl_seconds if s.data_mode == "live" else None


def cached(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        key = (fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items())))
        now, ttl = time.monotonic(), _ttl()
        with _lock:
            hit = _store.get(key)
        if hit and (ttl is None or now - hit[0] < ttl):
            return hit[1]
        val = fn(*args, **kwargs)
        with _lock:
            _store[key] = (now, val)
        return val
    wrapper.uncached = fn
    return wrapper


def clear() -> None:
    with _lock:
        _store.clear()
