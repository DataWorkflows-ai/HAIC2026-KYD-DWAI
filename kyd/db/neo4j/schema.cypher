// KYD graph model (Neo4j 5). Relationships, lineage and verification status only.
// Numbers stay in the fact store (kyd.sqlite / Postgres); nodes reference them by indicator id.
// Loaded by kyd/etl/build_graph.py from app/services/graph_data.py — see that file for the full model.
//
// (:District)-[:IN_COUNTY]->(:County)
// (:District {chamber:'house'})-[:OVERLAPS {share_of_house, share_of_senate}]->(:District {chamber:'senate'})
// (:District)-[:PEER_OF {rank}]->(:District)
// (:Legislator)-[:REPRESENTS]->(:District)
// (:District)-[:CONTAINS {rank}]->(:Neighborhood)
// (:NeighborhoodBoard|:CouncilDistrict)-[:COVERS {share}]->(:District)
// (:Program)-[:ADMINISTERED_BY]->(:Agency), (:Program)-[:SERVES]->(:Population)
// (:Program)-[:HAS_RULE]->(:Rule)-[:PROXIED_BY]->(:Indicator)
// (:Indicator)-[:DERIVED_FROM]->(:SourceTable)-[:PUBLISHED_BY]->(:Source)
// (:Dataset)-[:FEEDS]->(:Capability)-[:FOR_PROGRAM]->(:Program)
// (:Check)-[:CHECKS]->(:Dataset), (:IngestRun)-[:LOADED]->(:Dataset)

CREATE CONSTRAINT district_id IF NOT EXISTS FOR (n:District) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT county_id IF NOT EXISTS FOR (n:County) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT legislator_id IF NOT EXISTS FOR (n:Legislator) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT neighborhood_id IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT board_id IF NOT EXISTS FOR (n:NeighborhoodBoard) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT council_id IF NOT EXISTS FOR (n:CouncilDistrict) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT program_id IF NOT EXISTS FOR (n:Program) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT agency_id IF NOT EXISTS FOR (n:Agency) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT population_id IF NOT EXISTS FOR (n:Population) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (n:Rule) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT indicator_id IF NOT EXISTS FOR (n:Indicator) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_table_id IF NOT EXISTS FOR (n:SourceTable) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (n:Dataset) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT capability_id IF NOT EXISTS FOR (n:Capability) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT check_id IF NOT EXISTS FOR (n:Check) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ingest_run_id IF NOT EXISTS FOR (n:IngestRun) REQUIRE n.id IS UNIQUE;
CREATE FULLTEXT INDEX place_names IF NOT EXISTS FOR (n:Neighborhood|District|NeighborhoodBoard) ON EACH [n.name];
CREATE FULLTEXT INDEX program_text IF NOT EXISTS FOR (n:Program) ON EACH [n.name, n.summary];
