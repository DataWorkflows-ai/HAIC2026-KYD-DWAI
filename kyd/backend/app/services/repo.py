"""Fact repository. The only path by which numbers enter the system (§2.1)."""
from __future__ import annotations
import json
from typing import Protocol
from ..config import settings
from ..models import Geography, Observation, Source
from .quality import apply_flags


class FactRepo(Protocol):
    demo: bool
    def geographies(self, geo_type: str | None = None) -> list[Geography]: ...
    def geography(self, geo_id: str) -> Geography | None: ...
    def observations(self, geo_ids: list[str], indicators: list[str] | None = None) -> list[Observation]: ...
    def observation(self, obs_id: str) -> Observation | None: ...
    def indicators(self) -> list[dict]: ...
    def sources(self) -> list[Source]: ...


class FixtureRepo:
    """Reads synthetic JSON fixtures. Every observation is flagged 'demo'."""
    demo = True
    backend = "fixture"

    def __init__(self) -> None:
        d = settings().fixtures_dir
        load = lambda n: json.loads((d / f"{n}.json").read_text(encoding="utf-8"))
        self._geos = {g["geo_id"]: Geography(**g) for g in load("geographies")}
        self._sources = {s["source_id"]: Source(**s) for s in load("sources")}
        raw = load("observations")
        self._ind = {}
        self._obs: dict[str, Observation] = {}
        for r in raw:
            self._ind.setdefault(r["indicator"], {k: r[k] for k in ("indicator", "label", "unit", "topic", "acs")})
            o = Observation(**{k: v for k, v in r.items() if k in Observation.model_fields})
            rel = self._sources[o.source_id].release_date
            self._obs[o.obs_id] = apply_flags(o, rel, demo=True)

    def geographies(self, geo_type=None):
        return [g for g in self._geos.values() if geo_type in (None, g.geo_type)]

    def geography(self, geo_id):
        return self._geos.get(geo_id)

    def observations(self, geo_ids, indicators=None):
        idx = getattr(self, "_by_geo", None)
        if idx is None:   # built once: geo_id → observations, so lookups don't scan every row
            idx = self._by_geo = {}
            for o in self._obs.values():
                idx.setdefault(o.geo_id, []).append(o)
        ins = set(indicators or [])
        return [o for g in dict.fromkeys(geo_ids) for o in idx.get(g, ()) if not ins or o.indicator in ins]

    def observation(self, obs_id):
        return self._obs.get(obs_id)

    def indicators(self):
        return list(self._ind.values())

    def sources(self):
        return list(self._sources.values())


def _fill(self, geos, sources, indicators, observations) -> None:
    """Build the in-memory tables from rows (dicts). Shared by the SQLite and Postgres repositories, so both
    hold the same objects in the same order."""
    self._geos = {r["geo_id"]: Geography(geo_id=r["geo_id"], geo_type=r["geo_type"], name=r["name"],
                                         counties=[x for x in json.loads(r["counties"]) if x]) for r in geos}
    self._sources = {r["source_id"]: Source(**{k: r[k] for k in Source.model_fields if k in r}) for r in sources}
    self._ind = {r["indicator"]: dict(r) for r in indicators}
    self._obs: dict[str, Observation] = {}
    for r in observations:
        i = self._ind[r["indicator"]]
        o = Observation(obs_id=r["obs_id"], geo_id=r["geo_id"], indicator=r["indicator"], label=i["label"],
                        unit=i["unit"], value=r["value"], moe=r["moe"], vintage=r["vintage"],
                        method=r["method"], method_note=r["method_note"], source_id=r["source_id"])
        self._obs[o.obs_id] = apply_flags(o, self._sources[o.source_id].release_date)


class SqliteRepo:
    """Default mode. Bundled real data in kyd/data/kyd.sqlite, built by etl/load_acs_profile.py.
    Needs no database server, so judges can run the app as-is."""
    demo = False
    backend = "sqlite"

    def __init__(self) -> None:
        import sqlite3
        path = settings().data_dir / "kyd.sqlite"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing. Run: python kyd/etl/load_acs_profile.py")
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        c.row_factory = sqlite3.Row
        rows = lambda t: [dict(r) for r in c.execute(f"SELECT * FROM {t}")]
        _fill(self, rows("geography"), rows("source"), rows("indicator"), rows("observation"))
        c.close()

    geographies = FixtureRepo.geographies
    geography = FixtureRepo.geography
    observations = FixtureRepo.observations
    observation = FixtureRepo.observation
    indicators = FixtureRepo.indicators
    sources = FixtureRepo.sources


class PostgresRepo:
    """Live mode. Reads the kyd.* tables (db/live.sql, loaded by etl/promote_to_postgres.py) once at start-up
    and serves from memory, exactly like SqliteRepo. The connection pool stays open for the audit log."""
    demo = False
    backend = "postgres"

    def __init__(self, load: bool = True) -> None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool
        # A pool, not one shared connection: FastAPI serves requests on a thread pool, and a single psycopg
        # connection serializes (and can interleave) concurrent queries. prepare_threshold=None keeps it safe
        # behind a connection pooler (Supabase).
        self._pool = ConnectionPool(settings().database_url, min_size=1, max_size=settings().pg_pool_max,
                                    kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
                                    check=ConnectionPool.check_connection, open=True)
        if not load:
            return
        try:
            self._pool.wait(timeout=settings().pg_connect_timeout)
            rows = lambda t: [{k: v for k, v in r.items() if k != "ord"}
                              for r in self._q(f"SELECT * FROM kyd.{t} ORDER BY ord")]
            _fill(self, rows("geography"), rows("source"), rows("indicator"), rows("observation"))
            if not self._obs:
                raise RuntimeError("kyd.observation is empty. Run: python kyd/etl/promote_to_postgres.py")
            run = self._q("SELECT run_id, loaded_at::text, git_sha, sqlite_sha256, counts FROM kyd.load_run "
                          "ORDER BY run_id DESC LIMIT 1")
            self.load_run = run[0] if run else None
        except Exception:
            self._pool.close()
            raise

    def _q(self, sql, *args):
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def close(self) -> None:
        self._pool.close()

    geographies = FixtureRepo.geographies
    geography = FixtureRepo.geography
    observations = FixtureRepo.observations
    observation = FixtureRepo.observation
    indicators = FixtureRepo.indicators
    sources = FixtureRepo.sources


_repo: FactRepo | None = None


def repo() -> FactRepo:
    global _repo
    if _repo is None:
        mode = settings().data_mode
        if mode == "live":
            try:
                _repo = PostgresRepo()
            except Exception as e:   # database unreachable or not loaded: serve the bundled copy, and say so
                if not settings().live_fallback:
                    raise
                _repo = SqliteRepo()
                _repo.fallback_reason = f"{type(e).__name__}: {str(e)[:200]}"
        else:
            _repo = FixtureRepo() if mode == "fixture" else SqliteRepo()
    return _repo
