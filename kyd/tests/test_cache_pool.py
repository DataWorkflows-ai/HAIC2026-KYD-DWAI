"""Derived-result cache and the pooled Postgres repo (no database needed: the pool is faked)."""
import sys
import types

from app.agent import tools
from app.config import settings
from app.services import cache
from app.services.repo import PostgresRepo


def test_cached_results_are_reused_and_cleared():
    cache.clear()
    a = tools._rank_programs("HD-13")
    assert tools._rank_programs("HD-13") is a                          # served from cache
    assert [m.program.program_id for m in tools.find_programs("HD-13", limit=3)] == \
           [m.program.program_id for m in a[:3]]
    assert tools._rank_programs.uncached("HD-13") == a                 # cache does not change the answer
    cache.clear()
    assert tools._rank_programs("HD-13") is not a


def test_live_mode_entries_expire(monkeypatch):
    cache.clear()
    calls = []

    @cache.cached
    def f(x):
        calls.append(x)
        return x

    monkeypatch.setattr(settings(), "data_mode", "live")
    monkeypatch.setattr(settings(), "cache_ttl_seconds", 0)
    f(1); f(1)
    assert calls == [1, 1]                                             # TTL 0 → recomputed
    monkeypatch.setattr(settings(), "cache_ttl_seconds", 300)
    f(2); f(2)
    assert calls == [1, 1, 2]


def test_postgres_repo_uses_a_pool(monkeypatch):
    opened = []

    class Cur:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql, args): self.args = args
        def fetchall(self): return [{"ok": 1}]

    class Conn:
        def __enter__(self): opened.append(1); return self
        def __exit__(self, *a): pass
        def cursor(self): return Cur()

    class Pool:
        def __init__(self, url, min_size, max_size, kwargs, open):
            self.max_size = max_size
        def connection(self): return Conn()
        def close(self): pass

    monkeypatch.setitem(sys.modules, "psycopg_pool", types.SimpleNamespace(ConnectionPool=Pool))
    r = PostgresRepo()
    assert r._pool.max_size == settings().pg_pool_max
    assert r._q("select 1") == [{"ok": 1}] and r._q("select 2") == [{"ok": 1}]
    assert len(opened) == 2                                            # a pooled connection per query
