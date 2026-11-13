"""Program and lineage graph (Neo4j). Holds relationships only. Numbers are fetched from FactRepo."""
from __future__ import annotations
import json
from typing import Protocol
from ..config import settings
from ..models import Program


class ProgramGraph(Protocol):
    def programs(self) -> list[Program]: ...
    def program(self, program_id: str) -> Program | None: ...
    def programs_for_indicators(self, indicators: list[str]) -> list[Program]: ...
    def related(self, program_id: str) -> list[dict]: ...
    def lineage(self, indicator: str) -> list[dict]: ...


class FixtureGraph:
    def __init__(self) -> None:
        raw = json.loads((settings().data_dir / "programs.json").read_text(encoding="utf-8"))
        self._p = {r["program_id"]: Program(**{k: v for k, v in r.items() if k in Program.model_fields}) for r in raw}

    def programs(self):
        return list(self._p.values())

    def program(self, program_id):
        return self._p.get(program_id)

    def programs_for_indicators(self, indicators):
        s = set(indicators)
        return [p for p in self._p.values() if s & set(p.proxy_indicators)]

    def related(self, program_id):
        me = self._p.get(program_id)
        if not me:
            return []
        return [{"program_id": p.program_id, "kind": "shared_population"}
                for p in self._p.values() if p.program_id != program_id and set(p.populations) & set(me.populations)]

    def lineage(self, indicator):
        from .repo import repo
        r = repo()
        ind = next((i for i in r.indicators() if i["indicator"] == indicator), None)
        return [{"indicator": indicator, "table": ind.get("acs") if ind else None, "source_id": s.source_id,
                 "publisher": s.publisher} for s in r.sources()]


class Neo4jGraph:
    def __init__(self) -> None:
        from neo4j import GraphDatabase
        s = settings()
        self._d = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))

    def _q(self, cypher, **params):
        recs, _, _ = self._d.execute_query(cypher, params, database_="neo4j")
        return [r.data() for r in recs]

    _P = """MATCH (p:Program)
            OPTIONAL MATCH (p)-[:ADMINISTERED_BY]->(a:Agency)
            OPTIONAL MATCH (p)-[:SERVES]->(pop:Population)
            OPTIONAL MATCH (p)-[:HAS_RULE]->(:Rule)-[:PROXIED_BY]->(i:Indicator)
            WITH p, a, collect(DISTINCT pop.id) AS pops, collect(DISTINCT i.id) AS inds
            {where}
            RETURN p.id AS program_id, p.name AS name, coalesce(a.name,'') AS agency, p.level AS level,
                   coalesce(p.summary,'') AS summary, p.official_url AS official_url,
                   pops AS populations, inds AS proxy_indicators"""

    def programs(self):
        return [Program(**r) for r in self._q(self._P.format(where=""))]

    def program(self, program_id):
        r = self._q(self._P.format(where="WHERE p.id = $pid"), pid=program_id)
        return Program(**r[0]) if r else None

    def programs_for_indicators(self, indicators):
        return [Program(**r) for r in self._q(
            self._P.format(where="WHERE any(x IN inds WHERE x IN $inds)"), inds=indicators)]

    def related(self, program_id):
        return self._q("""MATCH (p:Program {id:$pid})-[r:RELATED_TO]-(q:Program)
                          RETURN q.id AS program_id, r.kind AS kind""", pid=program_id)

    def lineage(self, indicator):
        return self._q("""MATCH (i:Indicator {id:$ind})-[:DERIVED_FROM]->(t:SourceTable)-[:PUBLISHED_BY]->(s:Source)
                          RETURN i.id AS indicator, t.id AS table, s.id AS source_id, s.publisher AS publisher""",
                       ind=indicator)


_g: ProgramGraph | None = None


def graph() -> ProgramGraph:
    global _g
    if _g is None:
        _g = Neo4jGraph() if settings().data_mode == "live" else FixtureGraph()
    return _g
