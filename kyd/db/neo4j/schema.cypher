// KYD graph model (Neo4j 5). Holds relationships and lineage. Numbers stay in
// Postgres facts.observation; graph nodes reference them by indicator and obs_id.
//
// (:Program)-[:ADMINISTERED_BY]->(:Agency)
// (:Program)-[:SERVES]->(:Population)
// (:Program)-[:HAS_RULE]->(:Rule)-[:PROXIED_BY]->(:Indicator)
// (:Population)-[:MEASURED_BY]->(:Indicator)
// (:Program)-[:RELATED_TO {kind:'stack'|'cliff'|'gateway'}]->(:Program)
// (:District)-[:IN_COUNTY {share}]->(:County)
// (:District)-[:PEER_OF {distance}]->(:District)
// (:Indicator)-[:DERIVED_FROM]->(:SourceTable)-[:PUBLISHED_BY]->(:Source)
// (:Dataset {vintage})-[:INGESTED_BY]->(:IngestRun)        // lineage (§6)

CREATE CONSTRAINT program_id IF NOT EXISTS FOR (n:Program) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT agency_id IF NOT EXISTS FOR (n:Agency) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT population_id IF NOT EXISTS FOR (n:Population) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT indicator_id IF NOT EXISTS FOR (n:Indicator) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (n:Rule) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT district_id IF NOT EXISTS FOR (n:District) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT county_id IF NOT EXISTS FOR (n:County) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_table_id IF NOT EXISTS FOR (n:SourceTable) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT dataset_id IF NOT EXISTS FOR (n:Dataset) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ingest_run_id IF NOT EXISTS FOR (n:IngestRun) REQUIRE n.id IS UNIQUE;
CREATE FULLTEXT INDEX program_text IF NOT EXISTS FOR (n:Program) ON EACH [n.name, n.summary];
