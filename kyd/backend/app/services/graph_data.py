"""The relationship graph as plain data: one builder, two consumers.

`build()` reads the committed data files and returns nodes and relationships. The same document
feeds the in-memory FixtureGraph and etl/build_graph.py (Neo4j), so both backends answer from
identical facts, and the Neo4j load can be checked by counting back what was written.

Model (labels → key property `id`):
  District, County, Legislator, Neighborhood, NeighborhoodBoard, CouncilDistrict,
  Program, Agency, Population, Rule, Indicator, SourceTable, Source,
  Dataset, Capability, Check, IngestRun
Relationships:
  (District)-[:IN_COUNTY]->(County)
  (District:House)-[:OVERLAPS {share_of_house, share_of_senate}]->(District:Senate)
  (District)-[:PEER_OF {rank}]->(District)
  (Legislator)-[:REPRESENTS]->(District)
  (District)-[:CONTAINS {rank}]->(Neighborhood)
  (NeighborhoodBoard|CouncilDistrict)-[:COVERS {share}]->(District)
  (Program)-[:ADMINISTERED_BY]->(Agency), (Program)-[:SERVES]->(Population),
  (Program)-[:HAS_RULE]->(Rule)-[:PROXIED_BY]->(Indicator)
  (Indicator)-[:DERIVED_FROM]->(SourceTable)-[:PUBLISHED_BY]->(Source)
  (Dataset)-[:FEEDS]->(Capability)-[:FOR_PROGRAM]->(Program)
  (Check)-[:CHECKS]->(Dataset)            only non-passing checks; pass counts sit on Dataset
  (IngestRun)-[:LOADED]->(Dataset)
"""
from __future__ import annotations
import csv
import json
import re
import unicodedata
from datetime import datetime, timezone

from ..config import settings

# Crystal's program capabilities (scripts/*.py) and the datasets each one reads.
CAPABILITIES = {
    "snap_gap": ("SNAP eligible-vs-enrolled gap", "snap",
                 ["census.S1701.house", "census.S1701.senate", "census.S2201.house", "census.S2201.senate",
                  "census.DP02.house", "census.DP02.senate", "processed.snap_demographics"]),
    "tanf_proxy": ("TANF/TAONF eligibility proxy", None, ["census.S1701.house", "census.S1701.senate"]),
    "tanf_by_island": ("TANF caseload by island", None,
                       ["dhs.bessd_sfy2026", "processed.bessd_csv", "processed.poverty_estimates", "dhs.databook2025"]),
    "tanf_underenrollment": ("TANF demographic under-enrollment", None,
                             ["census.S1701.house", "census.S1701.senate", "dhs.databook2025"]),
    "ga_proxy": ("General Assistance need lenses", None,
                 ["census.S1810.house", "census.S1810.senate", "census.S1701.house", "census.S1701.senate",
                  "census.DP05.house", "census.DP05.senate", "dhs.databook2025"]),
    "aabd": ("AABD need lenses", None,
             ["census.S1810.house", "census.S1810.senate", "census.S0103.senate", "census.DP02.house",
              "census.DP02.senate", "dhs.databook2025"]),
    "medquest": ("Med-QUEST enrollment and uninsured filter", "med_quest",
                 ["census.S2701.house", "census.S2701.senate", "dhs.databook2025"]),
    "county_snap": ("County SNAP participation", "snap", ["dhs.testimony_2025_10"]),
}


def slug(s: str) -> str:
    s = s.replace("ʻ", "").replace("‘", "").replace("'", "")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def build() -> dict:
    from .repo import repo
    from ..agent.tools import peer_districts
    d = settings().data_dir
    nodes: dict[str, dict[str, dict]] = {}
    rels: list[tuple[str, str, str, str, str, dict]] = []

    def node(lbl: str, id: str, **props) -> str:
        nodes.setdefault(lbl, {}).setdefault(id, {"id": id}).update({k: v for k, v in props.items() if v is not None})
        return id

    def rel(t: str, fl: str, fid: str, tl: str, tid: str, **props) -> None:
        rels.append((t, fl, fid, tl, tid, props))

    r = repo()
    counties = json.loads((d / "district_counties.json").read_text())
    for g in r.geographies():
        if g.geo_type not in ("sldl", "sldu"):
            continue
        node("District", g.geo_id, name=g.name, chamber="house" if g.geo_type == "sldl" else "senate",
             number=int(g.geo_id[3:]))
        c = counties.get(g.geo_id)
        if c:
            cid = f"county-{slug(c)}"
            node("County", cid, name={"Oahu": "City & County of Honolulu", "Hawaii": "Hawaiʻi County",
                                      "Maui": "Maui County", "Kauai": "Kauaʻi County"}.get(c, c))
            rel("IN_COUNTY", "District", g.geo_id, "County", cid)
        for rank, p in enumerate(peer_districts(g.geo_id), 1):
            rel("PEER_OF", "District", g.geo_id, "District", p, rank=rank)

    with (d / "district_overlap.csv").open() as f:
        for row in csv.DictReader(f):
            rel("OVERLAPS", "District", row["house_geo"], "District", row["senate_geo"],
                share_of_house=float(row["share_of_house"]), share_of_senate=float(row["share_of_senate"]))
    with (d / "legislators.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["name"]:
                lid = f"leg-{row['geo_id']}"
                node("Legislator", lid, name=row["name"], status=row["status"], source=row["source"] or None,
                     source_url=row["source_url"] or None)
                rel("REPRESENTS", "Legislator", lid, "District", row["geo_id"])

    local = d / "district_local.json"
    if local.exists():
        for gid, v in json.loads(local.read_text(encoding="utf-8"))["districts"].items():
            for rank, n in enumerate(v["neighborhoods"], 1):
                rel("CONTAINS", "District", gid, "Neighborhood", node("Neighborhood", f"nbhd-{slug(n)}", name=n), rank=rank)
            for b in v["boards"]:
                bid = node("NeighborhoodBoard", f"nb-{b['number']}", number=b["number"], name=b["name"])
                rel("COVERS", "NeighborhoodBoard", bid, "District", gid, share=b["share"])
            for c in v["council"]:
                cid = node("CouncilDistrict", f"council-{slug(c['body'])}-{c['number'] or 'at-large'}",
                           body=c["body"], number=c["number"], name=c["name"])
                rel("COVERS", "CouncilDistrict", cid, "District", gid, share=c["share"])

    for p in json.loads((d / "programs.json").read_text(encoding="utf-8")):
        node("Program", p["program_id"], name=p["name"], level=p["level"], summary=p["summary"],
             official_url=p["official_url"], agency=p["agency"],
             populations=p["populations"], proxy_indicators=p["proxy_indicators"])   # ordered, as in programs.json
        rel("ADMINISTERED_BY", "Program", p["program_id"], "Agency", node("Agency", p["agency"], name=p["agency"]))
        for pop in p["populations"]:
            rel("SERVES", "Program", p["program_id"], "Population", node("Population", pop, name=pop))
        for ind in p["proxy_indicators"]:
            rid = node("Rule", f"{p['program_id']}:{ind}", kind="population_proxy")
            rel("HAS_RULE", "Program", p["program_id"], "Rule", rid)
            rel("PROXIED_BY", "Rule", rid, "Indicator", node("Indicator", ind))

    srcs = {s.source_id: s for s in r.sources()}
    for s in srcs.values():
        node("Source", s.source_id, publisher=s.publisher, title=s.title, url=s.url, release_date=s.release_date)
    default_src = next(iter(srcs), None)
    for i in r.indicators():
        node("Indicator", i["indicator"], label=i.get("label"), unit=i.get("unit"), topic=i.get("topic"))
        if i.get("acs"):
            node("SourceTable", i["acs"], table=str(i["acs"]).split("_")[0])
            rel("DERIVED_FROM", "Indicator", i["indicator"], "SourceTable", i["acs"])
            if default_src:
                rel("PUBLISHED_BY", "SourceTable", i["acs"], "Source", default_src)

    # verification: datasets, their latest check results, the run that produced them
    rp = d / "verification_report.json"
    if rp.exists():
        report = json.loads(rp.read_text(encoding="utf-8"))
        run_id = f"verify-{report['generated_at']}"
        node("IngestRun", run_id, at=report["generated_at"], git_sha=report.get("git_sha"),
             passed=report["summary"]["pass"], warned=report["summary"]["warn"], failed=report["summary"]["fail"])
        counts: dict[str, dict[str, int]] = {}
        for c in report["checks"]:
            counts.setdefault(c["source"], {"pass": 0, "info": 0, "warn": 0, "fail": 0})[c["status"]] += 1
        for sid, s in report["sources"].items():
            k = counts.get(sid, {})
            status = "fail" if k.get("fail") else "warn" if k.get("warn") else "pass"
            node("Dataset", sid, path=s.get("path"), url=s.get("url"), publisher=s.get("publisher"),
                 sha256=s.get("sha256"), verified_at=s.get("verified_at"), status=status,
                 checks_pass=k.get("pass", 0), checks_warn=k.get("warn", 0), checks_fail=k.get("fail", 0))
            rel("LOADED", "IngestRun", run_id, "Dataset", sid)
        for c in report["checks"]:
            if c["status"] in ("warn", "fail") and c["source"] in nodes.get("Dataset", {}):
                node("Check", c["id"], status=c["status"], kind=c["kind"], detail=c["detail"])
                rel("CHECKS", "Check", c["id"], "Dataset", c["source"])
        for cap, (label, prog, datasets) in CAPABILITIES.items():
            node("Capability", cap, name=label, script=f"scripts/{cap}.py")
            if prog:
                rel("FOR_PROGRAM", "Capability", cap, "Program", prog)
            for ds in datasets:
                if ds in nodes.get("Dataset", {}):
                    rel("FEEDS", "Dataset", ds, "Capability", cap)

    built = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"built_at": built, "nodes": {k: list(v.values()) for k, v in nodes.items()}, "rels": rels}
