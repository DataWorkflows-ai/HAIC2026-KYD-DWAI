"""Relationship graph: the in-memory backend always; Neo4j too when KYD_TEST_NEO4J=1 (CI loads it first
with etl/build_graph.py). Both must give identical answers."""
import os
import re

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import district_connections
from app.main import app
from app.services import representation as rep
from app.services.graph import FixtureGraph

c = TestClient(app)
mem = FixtureGraph()
DISTRICTS = [f"HD-{i:02d}" for i in range(1, 52)] + [f"SD-{i:02d}" for i in range(1, 26)]


def test_graph_context_matches_source_files():
    for g in DISTRICTS:
        ctx = mem.district_context(g)
        assert ctx and ctx["neighborhoods"] == rep.local_areas(g)["neighborhoods"], g
        assert [x["geo_id"] for x in ctx["counterparts"]] == [x["geo_id"] for x in rep.counterparts(g)], g
        assert ctx["council"], g


def test_connections_and_path():
    c19 = mem.connections("HD-19", "SD-09")
    assert c19["overlap"] > 0.95 and c19["same_county"] and c19["path"][0].startswith("District:")
    assert "Honolulu City Council 4" in mem.connections("HD-19", "HD-20")["shared_council"]
    assert not mem.connections("HD-01", "HD-40")["same_county"]


def test_capabilities_reflect_verification():
    caps = {x["capability"]: x for x in mem.capabilities()}
    assert {"snap_gap", "tanf_proxy", "ga_proxy", "aabd", "medquest"} <= set(caps)
    assert all(x["status"] != "fail" for x in caps.values())
    assert caps["snap_gap"]["program_id"] == "snap"


def test_connection_tool_has_no_statistics():
    for out in (district_connections("HD-19"), district_connections("HD-19", "SD-09")):
        text = str(out)
        assert "%" not in text and not re.search(r"\d\.\d", text)


def test_api_endpoints():
    assert c.get("/api/districts/HD-19/context").json()["county"] == "City & County of Honolulu"
    assert c.get("/api/connections?a=HD-19&b=HD-20").json()["peers"] in (True, False)
    v = c.get("/api/verification").json()
    assert v["summary"]["fail"] == 0 and v["capabilities"]
    assert c.get("/api/health").json()["graph"] in ("memory", "neo4j")


@pytest.mark.skipif(os.getenv("KYD_TEST_NEO4J") != "1", reason="Neo4j integration (set KYD_TEST_NEO4J=1)")
def test_neo4j_matches_memory():
    from app.services.graph import Neo4jGraph
    neo = Neo4jGraph()
    for g in DISTRICTS:
        assert neo.district_context(g) == mem.district_context(g), g
    for a, b in (("HD-19", "SD-09"), ("HD-19", "HD-20"), ("HD-01", "HD-40")):
        x, y = neo.connections(a, b), mem.connections(a, b)
        assert {k: v for k, v in x.items() if k != "path"} == {k: v for k, v in y.items() if k != "path"}
        assert len(x["path"]) == len(y["path"])            # same shortest length; ties may pick other nodes
    assert neo.capabilities() == mem.capabilities()
    assert [p.model_dump() for p in neo.programs()] == [p.model_dump() for p in mem.programs()]
    assert neo.lineage("pct_below_fpl") == mem.lineage("pct_below_fpl")
