# Legislative district boundaries

Official statewide boundaries used by the comparison map. They are saved in the
project and are not downloaded when the app runs.

## Source

- Service: Hawaiʻi Statewide GIS Program, AdminBnd MapServer
  https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer
- House: layer 33, “State House Districts 22”
  https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/33
- Senate: layer 34, “State Senate Districts 22”
  https://geodata.hawaii.gov/arcgis/rest/services/AdminBnd/MapServer/34
- Retrieval date: 2026-11-05
- Query: `where=1=1`, `outFields=*`, `returnGeometry=true`, `outSR=4326`, `f=geojson`

## Vintage

2022 Hawaiʻi State House and Senate district boundaries as adopted by the State
of Hawaiʻi Reapportionment Commission in 2022. Source: State of Hawaiʻi Office
of Elections; Hawaiʻi Statewide GIS Program.

Metadata:
- https://files.hawaii.gov/dbedt/op/gis/data/house22.pdf
- https://files.hawaii.gov/dbedt/op/gis/data/senate22.pdf
- https://files.hawaii.gov/dbedt/op/gis/data/legislative_districts_2022.pdf

## Identifiers

- House: `house_id`, numeric 1–51. Short name `state_house` (H01–H51).
- Senate: `senate_id`, numeric 1–25. Short name `state_senate` (S01–S25).
- One feature per district. Islands that belong to the same district are parts
  of that one feature, not separate district identifiers.

## Match to ACS geography

The committed ACS 2020–2024 five-year tables from DBEDT use the current state
legislative districts, numbered House 1–51 and Senate 1–25. Those are the 2022
reapportionment districts in effect for the 2024 ACS legislative-district
tabulation. District identifiers join one-to-one. No mismatch was found.

## Attribution

State of Hawaiʻi Office of Elections; Hawaiʻi Statewide GIS Program. The GIS
data do not represent or confer legal boundaries, rights, or claims. They show
district geography only, not the location of individual households.
