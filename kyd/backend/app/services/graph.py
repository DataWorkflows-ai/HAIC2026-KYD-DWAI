"""Relationship graph: programs, districts, neighborhoods, lineage and verification status.
Holds relationships only; numbers come from FactRepo.

Backends (KYD_GRAPH_MODE):
  auto     Neo4j if it answers within ~2 s, otherwise the in-memory graph (default)
  neo4j    Neo4j or fail at startup
  fixture  in-memory graph only
Both backends are built from the same document (graph_data.build), so answers match.
"""
from __future__ import annotations
import logging
from collections import defaultdict, deque
from typing import Protocol

from ..config import settings
from ..models import Program
from . import datastore

log = logging.getLogger("kyd.graph")


class ProgramGraph(Protocol):
    backend: str
    def programs(self) -> list[Program]: ...
    def program(self, program_id: str) -> Program | None: ...
    def programs_for_indicators(self, indicators: list[str]) -> list[Program]: ...
    def related(self, program_id: str) -> list[dict]: ...
    def lineage(self, indicator: str) -> list[dict]: ...
    def district_context(self, geo_id: str) -> dict | None: ...
    def connections(self, a: str, b: str) -> dict: ...
    def capabilities(self) -> list[dict]: ...


def _program_from_json() -> dict[str, Program]:
    raw = datastore.load_json("programs.json")
    return {r["program_id"]: Program(**{k: v for k, v in r.items() if k in Program.model_fields}) for r in raw}


class FixtureGraph:
    """In-memory graph built from graph_data.build()."""
    backend = "memory"

    def __init__(self) -> None:
        from .graph_data import build
        self._p = _program_from_json()
        doc = build()
        self._n = {lbl: {n["id"]: n for n in ns} for lbl, ns in doc["nodes"].items()}
        self._out: dict[tuple[str, str], list[tuple[str, str, str, dict]]] = defaultdict(list)
        self._in: dict[tuple[str, str], list[tuple[str, str, str, dict]]] = defaultdict(list)
        for t, fl, fid, tl, tid, props in doc["rels"]:
            self._out[(fl, fid)].append((t, tl, tid, props))
            self._in[(tl, tid)].append((t, fl, fid, props))

    # programs ---------------------------------------------------------------
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
        out = []
        for t, tl, tid, _ in self._out[("Indicator", indicator)]:
            if t != "DERIVED_FROM":
                continue
            for t2, _, sid, _ in self._out[("SourceTable", tid)]:
                if t2 == "PUBLISHED_BY":
                    out.append({"indicator": indicator, "table": tid, "source_id": sid,
                                "publisher": self._n["Source"][sid].get("publisher")})
        return out

    # districts --------------------------------------------------------------
    def district_context(self, geo_id):
        if geo_id not in self._n.get("District", {}):
            return None
        out, inc = self._out[("District", geo_id)], self._in[("District", geo_id)]
        house = geo_id.startswith("HD")
        overl = [(p["share_of_house"] if house else p["share_of_senate"], oid)
                 for t, _, oid, p in (out if house else inc) if t == "OVERLAPS"]
        leg = next((self._n["Legislator"][lid] for t, _, lid, _ in inc if t == "REPRESENTS"), None)
        county = next((self._n["County"][cid]["name"] for t, _, cid, _ in out if t == "IN_COUNTY"), None)
        return {
            "geo_id": geo_id, "name": self._n["District"][geo_id]["name"], "county": county,
            "legislator": {"name": leg["name"], "status": leg["status"]} if leg else None,
            "counterparts": [{"geo_id": g, "share_of_this": s} for s, g in sorted(overl, key=lambda x: (-x[0], x[1]))],
            "peers": [g for _, g, r in sorted((p["rank"], g, p) for t, _, g, p in out if t == "PEER_OF")],
            "neighborhoods": [self._n["Neighborhood"][n]["name"]
                              for _, n in sorted((p["rank"], n) for t, _, n, p in out if t == "CONTAINS")],
            "boards": sorted(({"number": self._n["NeighborhoodBoard"][b]["number"],
                               "name": self._n["NeighborhoodBoard"][b]["name"], "share": p["share"]}
                              for t, lbl, b, p in inc if t == "COVERS" and lbl == "NeighborhoodBoard"),
                             key=lambda x: (-x["share"], x["number"])),
            "council": sorted(({"body": self._n["CouncilDistrict"][c]["body"],
                                "number": self._n["CouncilDistrict"][c].get("number"),
                                "name": self._n["CouncilDistrict"][c].get("name"), "share": p["share"]}
                               for t, lbl, c, p in inc if t == "COVERS" and lbl == "CouncilDistrict"),
                              key=lambda x: (-x["share"], x["body"], x["number"] or 0)),
        }

    def connections(self, a, b):
        A, B = self.district_context(a), self.district_context(b)
        if not A or not B:
            return {"a": a, "b": b, "error": "unknown district"}
        bk = lambda xs: {(x["body"], x["number"]) for x in xs}
        return {
            "a": a, "b": b, "same_county": A["county"] == B["county"],
            "overlap": next((c["share_of_this"] for c in A["counterparts"] if c["geo_id"] == b), None),
            "peers": b in A["peers"] or a in B["peers"],
            "shared_neighborhoods": sorted(set(A["neighborhoods"]) & set(B["neighborhoods"])),
            "shared_boards": sorted({x["number"] for x in A["boards"]} & {x["number"] for x in B["boards"]}),
            "shared_council": sorted(f"{body} {n or ''}".strip() for body, n in bk(A["council"]) & bk(B["council"])),
            "path": self._path(a, b),
        }

    def _path(self, a, b, max_hops=4) -> list[str]:
        """Shortest undirected path between two districts through any shared entity."""
        start, goal = ("District", a), ("District", b)
        prev = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == goal:
                break
            depth, x = 0, cur
            while prev[x]:
                x, depth = prev[x], depth + 1
            if depth >= max_hops:
                continue
            for _, lbl, nid, _ in self._out[cur] + self._in[cur]:
                nxt = (lbl, nid)
                if nxt not in prev and lbl not in ("Legislator", "Program", "Rule", "Indicator"):
                    prev[nxt] = cur
                    q.append(nxt)
        if goal not in prev:
            return []
        out, x = [], goal
        while x:
            n = self._n[x[0]][x[1]]
            out.append(f"{x[0]}:{n.get('name') or n['id']}")
            x = prev[x]
        return out[::-1]

    # verification -----------------------------------------------------------
    def capabilities(self):
        out = []
        for cid, cap in sorted(self._n.get("Capability", {}).items()):
            ds = [self._n["Dataset"][d] for t, _, d, _ in self._in[("Capability", cid)] if t == "FEEDS"]
            prog = next((p for t, _, p, _ in self._out[("Capability", cid)] if t == "FOR_PROGRAM"), None)
            status = "fail" if any(d["status"] == "fail" for d in ds) else \
                "warn" if any(d["status"] == "warn" for d in ds) else "pass"
            out.append({"capability": cid, "name": cap["name"], "program_id": prog, "status": status,
                        "datasets": sorted(({"id": d["id"], "status": d["status"], "verified_at": d.get("verified_at")}
                                            for d in ds), key=lambda x: x["id"])})
        return out


class Neo4jGraph:
    backend = "neo4j"

    def __init__(self, timeout: float = 5.0) -> None:
        from neo4j import GraphDatabase
        s = settings()
        self._d = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password),
                                       connection_timeout=timeout, max_connection_pool_size=20)
        self._d.verify_connectivity()
        self._p_cache: list[Program] | None = None

    def _q(self, cypher, **params):
        recs, _, _ = self._d.execute_query(cypher, params, database_="neo4j")
        return [r.data() for r in recs]

    # Lists are stored on the node in programs.json order: the first proxy indicator is the eligibility
    # proxy in find_programs, so order matters and must not come from an unordered collect().
    _P = """MATCH (p:Program)
            RETURN p.id AS program_id, p.name AS name, coalesce(p.agency,'') AS agency, p.level AS level,
                   coalesce(p.summary,'') AS summary, p.official_url AS official_url,
                   coalesce(p.populations, []) AS populations, coalesce(p.proxy_indicators, []) AS proxy_indicators"""

    def programs(self):
        if self._p_cache is None:
            order = {pid: i for i, pid in enumerate(_program_from_json())}
            self._p_cache = sorted((Program(**r) for r in self._q(self._P)), key=lambda p: order.get(p.program_id, 999))
        return self._p_cache

    def program(self, program_id):
        return next((p for p in self.programs() if p.program_id == program_id), None)

    def programs_for_indicators(self, indicators):
        s = set(indicators)
        return [p for p in self.programs() if s & set(p.proxy_indicators)]

    def related(self, program_id):
        return self._q("""MATCH (p:Program {id:$pid})-[:SERVES]->(:Population)<-[:SERVES]-(q:Program)
                          RETURN DISTINCT q.id AS program_id, 'shared_population' AS kind ORDER BY program_id""",
                       pid=program_id)

    def lineage(self, indicator):
        return self._q("""MATCH (i:Indicator {id:$ind})-[:DERIVED_FROM]->(t:SourceTable)-[:PUBLISHED_BY]->(s:Source)
                          RETURN i.id AS indicator, t.id AS table, s.id AS source_id, s.publisher AS publisher""",
                       ind=indicator)

    def district_context(self, geo_id):
        r = self._q("""
            MATCH (d:District {id:$g})
            OPTIONAL MATCH (d)-[:IN_COUNTY]->(c:County)
            OPTIONAL MATCH (l:Legislator)-[:REPRESENTS]->(d)
            CALL { WITH d OPTIONAL MATCH (d)-[o:OVERLAPS]-(x:District)
                       WITH x, CASE WHEN d.chamber = 'house' THEN o.share_of_house ELSE o.share_of_senate END AS s
                       ORDER BY s DESC, x.id RETURN collect(CASE WHEN x IS NULL THEN null ELSE {geo_id:x.id, share_of_this:s} END) AS counterparts }
            CALL { WITH d OPTIONAL MATCH (d)-[p:PEER_OF]->(x:District) WITH x, p ORDER BY p.rank
                       RETURN collect(x.id) AS peers }
            CALL { WITH d OPTIONAL MATCH (d)-[k:CONTAINS]->(n:Neighborhood) WITH n, k ORDER BY k.rank
                       RETURN collect(n.name) AS neighborhoods }
            CALL { WITH d OPTIONAL MATCH (b:NeighborhoodBoard)-[v:COVERS]->(d) WITH b, v ORDER BY v.share DESC, b.number
                       RETURN collect(CASE WHEN b IS NULL THEN null ELSE {number:b.number, name:b.name, share:v.share} END) AS boards }
            CALL { WITH d OPTIONAL MATCH (cd:CouncilDistrict)-[v:COVERS]->(d) WITH cd, v ORDER BY v.share DESC, cd.body, cd.number
                       RETURN collect(CASE WHEN cd IS NULL THEN null ELSE {body:cd.body, number:cd.number, name:cd.name, share:v.share} END) AS council }
            RETURN d.id AS geo_id, d.name AS name, c.name AS county,
                   CASE WHEN l IS NULL THEN null ELSE {name:l.name, status:l.status} END AS legislator,
                   counterparts, peers, neighborhoods, boards, council""", g=geo_id)
        if not r:
            return None
        out = r[0]
        for k in ("boards", "council"):
            out[k] = [{**x, "number": x.get("number"), "name": x.get("name")} for x in out[k]]
        return out

    def connections(self, a, b):
        A, B = self.district_context(a), self.district_context(b)
        if not A or not B:
            return {"a": a, "b": b, "error": "unknown district"}
        path = self._q("""
            MATCH (x:District {id:$a}), (y:District {id:$b})
            MATCH p = shortestPath((x)-[*..4]-(y))
            WHERE none(n IN nodes(p) WHERE n:Legislator OR n:Program OR n:Rule OR n:Indicator)
            RETURN [n IN nodes(p) | head(labels(n)) + ':' + coalesce(n.name, n.id)] AS path""", a=a, b=b)
        bk = lambda xs: {(x["body"], x["number"]) for x in xs}
        return {
            "a": a, "b": b, "same_county": A["county"] == B["county"],
            "overlap": next((c["share_of_this"] for c in A["counterparts"] if c["geo_id"] == b), None),
            "peers": b in A["peers"] or a in B["peers"],
            "shared_neighborhoods": sorted(set(A["neighborhoods"]) & set(B["neighborhoods"])),
            "shared_boards": sorted({x["number"] for x in A["boards"]} & {x["number"] for x in B["boards"]}),
            "shared_council": sorted(f"{body} {n or ''}".strip() for body, n in bk(A["council"]) & bk(B["council"])),
            "path": path[0]["path"] if path else [],
        }

    def capabilities(self):
        rows = self._q("""
            MATCH (c:Capability)
            OPTIONAL MATCH (c)-[:FOR_PROGRAM]->(p:Program)
            OPTIONAL MATCH (d:Dataset)-[:FEEDS]->(c)
            WITH c, p, d ORDER BY d.id
            RETURN c.id AS capability, c.name AS name, p.id AS program_id,
                   collect(CASE WHEN d IS NULL THEN null ELSE {id:d.id, status:d.status, verified_at:d.verified_at} END) AS datasets
            ORDER BY capability""")
        for r in rows:
            st = {d["status"] for d in r["datasets"]}
            r["status"] = "fail" if "fail" in st else "warn" if "warn" in st else "pass"
        return rows


_g: ProgramGraph | None = None


def graph() -> ProgramGraph:
    global _g
    if _g is None:
        s = settings()
        mode = s.graph_mode if s.graph_mode != "auto" or s.data_mode != "live" else "neo4j"
        if mode in ("auto", "neo4j"):
            try:
                _g = Neo4jGraph(timeout=2.0 if mode == "auto" else 10.0)
                log.info("graph backend: neo4j at %s", s.neo4j_uri)
            except Exception as e:
                if mode == "neo4j":
                    raise
                log.info("graph backend: in-memory (Neo4j unavailable: %s)", type(e).__name__)
        if _g is None:
            _g = FixtureGraph()
    return _g


def reset() -> None:
    global _g
    _g = None
