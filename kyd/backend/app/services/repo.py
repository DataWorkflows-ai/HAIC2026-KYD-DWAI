"""Fact repository (Postgres). The only path by which numbers enter the system (§2.1)."""
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
        gs, ins = set(geo_ids), set(indicators or [])
        return [o for o in self._obs.values() if o.geo_id in gs and (not ins or o.indicator in ins)]

    def observation(self, obs_id):
        return self._obs.get(obs_id)

    def indicators(self):
        return list(self._ind.values())

    def sources(self):
        return list(self._sources.values())


class PostgresRepo:
    """Live mode. Reads facts.observation (status = 'live') joined to its reference tables."""
    demo = False

    def __init__(self) -> None:
        import psycopg
        from psycopg.rows import dict_row
        self._conn = psycopg.connect(settings().database_url, row_factory=dict_row, autocommit=True)

    def _q(self, sql, *args):
        with self._conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def geographies(self, geo_type=None):
        rows = self._q("""SELECT geo_id, geo_type, name, coalesce(county_fips, '{}') AS counties
                          FROM ref.geography WHERE geo_type IN ('state','county','sldu','sldl')
                          AND (%s::text IS NULL OR geo_type = %s) ORDER BY geo_id""", geo_type, geo_type)
        return [Geography(**r) for r in rows]

    def geography(self, geo_id):
        g = [x for x in self.geographies() if x.geo_id == geo_id]
        return g[0] if g else None

    _OBS = """SELECT o.obs_id::text, o.geo_id, o.indicator, i.label, i.unit, o.value, o.moe, o.cv,
                     o.vintage, o.method, o.method_note, o.source_id, s.release_date::text AS release_date
              FROM facts.observation o JOIN ref.indicator i USING (indicator) JOIN ref.source s USING (source_id)
              WHERE o.status = 'live' """

    def _rows_to_obs(self, rows):
        out = []
        for r in rows:
            rel = r.pop("release_date")
            out.append(apply_flags(Observation(**r), rel))
        return out

    def observations(self, geo_ids, indicators=None):
        rows = self._q(self._OBS + "AND o.geo_id = ANY(%s) AND (%s::text[] IS NULL OR o.indicator = ANY(%s))",
                       geo_ids, indicators, indicators)
        return self._rows_to_obs(rows)

    def observation(self, obs_id):
        rows = self._q(self._OBS.replace("WHERE o.status = 'live'", "WHERE true") + "AND o.obs_id = %s::bigint", obs_id)
        return self._rows_to_obs(rows)[0] if rows else None

    def indicators(self):
        return self._q("SELECT indicator, label, unit, topic, acs_vars AS acs FROM ref.indicator ORDER BY topic")

    def sources(self):
        return [Source(**r) for r in self._q(
            "SELECT source_id, publisher, title, url, release_date::text, license FROM ref.source")]


_repo: FactRepo | None = None


def repo() -> FactRepo:
    global _repo
    if _repo is None:
        _repo = PostgresRepo() if settings().data_mode == "live" else FixtureRepo()
    return _repo
