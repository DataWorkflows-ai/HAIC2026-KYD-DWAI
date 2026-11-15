"""Seed Neo4j from backend/fixtures/programs.json (later: from programs/*.json).
Usage: KYD_NEO4J_PASSWORD=... python etl/seed_graph.py"""
import json, os
from pathlib import Path
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
drv = GraphDatabase.driver(os.getenv("KYD_NEO4J_URI", "bolt://127.0.0.1:7688"),
                           auth=("neo4j", os.getenv("KYD_NEO4J_PASSWORD", "kyd_dev_pw")))
for stmt in (ROOT / "db/neo4j/schema.cypher").read_text().split(";"):
    body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("//")).strip()
    if body:
        drv.execute_query(body)
programs = json.loads((ROOT / "backend/fixtures/programs.json").read_text(encoding="utf-8"))
drv.execute_query("""
UNWIND $ps AS p
MERGE (prog:Program {id: p.program_id})
  SET prog.name = p.name, prog.level = p.level, prog.summary = p.summary, prog.official_url = p.official_url
MERGE (a:Agency {id: p.agency}) SET a.name = p.agency
MERGE (prog)-[:ADMINISTERED_BY]->(a)
FOREACH (pop IN p.populations | MERGE (x:Population {id: pop}) MERGE (prog)-[:SERVES]->(x))
FOREACH (ind IN p.proxy_indicators |
  MERGE (i:Indicator {id: ind})
  MERGE (r:Rule {id: p.program_id + ':' + ind}) SET r.kind = 'population_proxy'
  MERGE (prog)-[:HAS_RULE]->(r) MERGE (r)-[:PROXIED_BY]->(i))
""", ps=programs)
drv.execute_query("""MATCH (a:Program)-[:SERVES]->(:Population)<-[:SERVES]-(b:Program) WHERE a.id < b.id
                     MERGE (a)-[:RELATED_TO {kind:'shared_population'}]->(b)""")
print(f"seeded {len(programs)} programs")
