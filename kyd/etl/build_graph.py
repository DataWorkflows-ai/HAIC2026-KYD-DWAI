"""Load the KYD relationship graph into Neo4j, then read it back to prove the load is complete.

  docker compose -f kyd/docker-compose.yml up -d graph
  python kyd/etl/build_graph.py                 # KYD_NEO4J_URI / KYD_NEO4J_PASSWORD from env or backend/.env

Steps
  1. build the graph document from the committed data files (app/services/graph_data.py)
  2. apply db/neo4j/schema.cypher (constraints, full-text indexes)
  3. MERGE every node and relationship, stamped with this build's id
  4. delete nodes and relationships left over from earlier builds
  5. verify: node and relationship counts per label/type equal the document, and Neo4j answers
     district_context() exactly like the in-memory graph for every district
Exit code 1 if verification fails.
"""
from __future__ import annotations
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

KYD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KYD / "backend"))
os.environ.setdefault("KYD_DATA_MODE", "sqlite")

from app.config import settings  # noqa: E402
from app.services.graph import FixtureGraph, Neo4jGraph  # noqa: E402
from app.services.graph_data import build  # noqa: E402

BATCH = 1000


def apply_schema(drv) -> None:
    for stmt in (KYD / "db" / "neo4j" / "schema.cypher").read_text().split(";"):
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("//")).strip()
        if body:
            drv.execute_query(body)


def main() -> int:
    from neo4j import GraphDatabase
    s = settings()
    doc = build()
    build_id = doc["built_at"]
    drv = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))
    drv.verify_connectivity()
    apply_schema(drv)

    for label, rows in doc["nodes"].items():
        for i in range(0, len(rows), BATCH):
            drv.execute_query(f"UNWIND $rows AS r MERGE (n:`{label}` {{id: r.id}}) SET n = r, n.build = $b",
                              rows=rows[i:i + BATCH], b=build_id)
    groups: dict[tuple[str, str, str], dict[tuple[str, str], dict]] = defaultdict(dict)
    for t, fl, fid, tl, tid, props in doc["rels"]:
        groups[(t, fl, tl)][(fid, tid)] = props          # one relationship per (type, from, to)
    for (t, fl, tl), rel in groups.items():
        rows = [{"f": f, "t": to, "p": p} for (f, to), p in rel.items()]
        for i in range(0, len(rows), BATCH):
            drv.execute_query(f"""UNWIND $rows AS r
                                 MATCH (a:`{fl}` {{id: r.f}}) MATCH (b:`{tl}` {{id: r.t}})
                                 MERGE (a)-[x:`{t}`]->(b) SET x = r.p, x.build = $b""", rows=rows[i:i + BATCH], b=build_id)

    labels = list(doc["nodes"])
    drv.execute_query("MATCH ()-[x]->() WHERE x.build IS NULL OR x.build <> $b DELETE x", b=build_id)
    drv.execute_query("MATCH (n) WHERE any(l IN labels(n) WHERE l IN $ls) AND (n.build IS NULL OR n.build <> $b) "
                      "DETACH DELETE n", ls=labels, b=build_id)

    # ── verify ────────────────────────────────────────────────────────────────
    problems = []
    want_n = {k: len(v) for k, v in doc["nodes"].items()}
    got_n = {r["l"]: r["n"] for r in drv.execute_query(
        "MATCH (n) WHERE n.build = $b UNWIND labels(n) AS l RETURN l, count(*) AS n", b=build_id).records}
    want_r = Counter()
    for (t, _, _), rel in groups.items():
        want_r[t] += len(rel)
    got_r = {r["t"]: r["n"] for r in drv.execute_query(
        "MATCH ()-[x]->() WHERE x.build = $b RETURN type(x) AS t, count(*) AS n", b=build_id).records}
    for k, v in want_n.items():
        if got_n.get(k) != v:
            problems.append(f"nodes {k}: wrote {v}, found {got_n.get(k)}")
    for k, v in want_r.items():
        if got_r.get(k) != v:
            problems.append(f"relationships {k}: wrote {v}, found {got_r.get(k)}")

    mem, neo = FixtureGraph(), Neo4jGraph()
    for gid in sorted(n["id"] for n in doc["nodes"]["District"]):
        a, b = mem.district_context(gid), neo.district_context(gid)
        if a != b:
            diff = [k for k in a if a.get(k) != b.get(k)]
            problems.append(f"district_context({gid}) differs in {diff}")
    if mem.capabilities() != neo.capabilities():
        problems.append("capabilities() differ between in-memory and Neo4j")

    print(f"graph build {build_id}: {sum(want_n.values())} nodes, {sum(want_r.values())} relationships "
          f"→ {s.neo4j_uri}")
    for p in problems:
        print("  MISMATCH", p)
    print("verified: Neo4j matches the source document" if not problems else f"{len(problems)} problems")
    drv.close()
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
