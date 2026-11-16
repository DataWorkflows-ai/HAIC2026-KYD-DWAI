# HPD beat polygons (APPROXIMATE) and beat → legislative-district shares

## 1. Search for official beat or district polygons: none found
- **ArcGIS Online** (`sharing/rest/search`): I searched "HPD beat", "police beat Honolulu", "patrol district Honolulu", "Honolulu police beats", "HPD districts", "police districts Oahu", "HPD sector", "Honolulu Police Department" and a boolean beat/district + Honolulu/Oahu/Hawaii query. Every hit was a Houston PD (also "HPD") layer, a police-station point layer, or a student project. None of the Honolulu results were beat or district polygons.
- **City GIS org** `services.arcgis.com/tNJpAOha4mODLkXz` (402 services): it has `Police` and `Public_Safety`, which are station points only, and no beat/sector/district layer.
- **State GIS** `geodata.hawaii.gov` EmergMgmtPubSafety: police stations (points) only.
- **data.honolulu.gov** (Socrata catalog): only *HPD Crime Incidents* (vg88-5rn5). It has block addresses and no beat or district field.
- **UIPA request #1152** (Tyler Chong, 2024-05-23) asked HPD for district 1–8 shapefiles. HPD replied 2024-07-31 with a "Notice to Requester" attachment that isn't published on the public page, and no shapefiles were posted. The request status is "awaits classification".
- **HPD site:** `/organization/patrol-districts/` and `/policy/policy-patrol-command-boundaries/` have text boundaries only. The policy confirms 158 motor beats.
- **Power BI dashboard:** deliberately not used. No internal querydata APIs were called and the Power BI map wasn't scraped.

So beat polygons were **traced from the beat-map images** in the HPD 2025 Annual Report (PDF pp. 35–49, odd pages). Mitchell said the D1 image attachment he mentioned wasn't on the box, so the report page was used for D1 too.

## 2. Tracing (scripts/segment_beats.py)
- Each map page was rendered at 150 dpi.
- District fill = blue pixels, plus yellow label boxes. Beats are separated by the white beat lines. Beat labels come from `pdftotext -bbox`, which gives the exact label positions, and each connected region is labeled by the beat label inside it.
- Unlabeled fragments and line pixels go to the nearest labeled region. When two labels fall in one region (lines too faint), the region is split by nearest label (Voronoi).
- Result: **all 158 beats traced, in all 8 districts.**

## 3. Georeferencing (APPROXIMATE)
The basemap is north-up Google Maps (Web Mercator), so each page is fitted with scale + translation in EPSG:3857, with no rotation.

| HPD district | page | method | m/px @150dpi | fit quality |
|---|---|---|---|---|
| 1 Central Honolulu | 35 | 4 manual control points: Bishop Museum, Punchbowl cemetery, Honolulu Museum of Art and Manoa Falls Trail POI pins | 6.96 | CP residuals 34–91 m |
| 2 Wahiawa | 37 | water/land agreement of basemap vs Oahu land polygon | 40.06 | balanced accuracy 0.979 |
| 3 Pearl City | 39 | Byodo-In Temple pin anchor + scale chosen to minimise overlap with D2/D4/D8. The Wheeler AAF label pair gives ~21 m/px independently. | 20.5 | overlap 1.9% |
| 4 Kaneohe | 41 | coastline match | 38.28 | 0.981 |
| 5 Kalihi | 43 | 3 control points: HoMA, UH Manoa and Manoa Falls Trail pins | 16.99 | residuals 55–140 m |
| 6 Waikiki | 45 | coastline match | 3.82 | 0.953 |
| 7 East Honolulu | 47 | coastline match | 17.49 | 0.992 |
| 8 Waianae | 49 | coastline match | 32.02 | 0.965 |

Rejected control points: Tantalus Lookout (inconsistent pin), Aloha Tower (pin hidden), Pearl Harbor National Memorial (ambiguous pin) and the generic "Military base" pin.

Two automated attempts were tried and discarded: fitting to neighbourhood-board approximations, and a joint tiling optimisation. They misplaced Districts 1, 3 and 5, as shown by overlapping districts.

**Final check:** the 8 traced districts tile Oahu with 1–3% overlap each and 98–100% on land. See `beat_gis/qa_overlay_*.png`. Expected positional error is about 50–150 m in town and a few hundred metres on the large rural pages (D2/D4/D8 at 32–40 m/px). Small shoreline and harbour slivers were clipped to the county land boundary.

## 4. Beat → district shares (scripts/join_beats_to_districts.py)
- **Projection:** EPSG:26904 (NAD83 / UTM 4N).
- **Districts:** 2022 State House and Senate layers and the Honolulu council layer from `gis_districts/`.
- **area_share** = beat land area inside the district ÷ beat land area.
- **pop_share** = 2020 Census DHC block population (higeo2020.dhc, internal points). There are 7,125 Honolulu blocks with 1,016,508 people, assigned to beats by point-in-polygon. 14,977 people were assigned to the nearest beat within 500 m (points falling in tracing gaps), and 0 people were left unassigned.
- **pop_share_or_area_if_pop_lt50** = pop_share, except for beats with fewer than 50 residents (airport, industrial and park beats), where area_share is used. This is the recommended weight for attributing crime.
- **Files:** `beat_to_house.csv`, `beat_to_senate.csv`, `beat_to_council.csv` and `multi_district_beats.csv`. A beat counts as multi-district if 2 or more districts each have ≥1% by area or pop. `material_split` = the second-largest weight is ≥10%.
- **Splits:**
  - House: 93 beats span >1 district (52 materially).
  - Senate: 73 (33 materially).
  - Council: 45 (19 materially).
  - Many 1–5% splits are within the georeferencing error, so treat them as noise.
- **Beat 264** (D2, Wahiawa area):
  - House: H46 98.8% pop / 73.4% area; H47 1.2% pop / 24.9% area; H45 0% pop / 1.7% area.
  - Senate: S23 84.0% pop / 96.9% area; S17 16.0% pop / 1.4% area.
  - Council: C2 100% pop.

## 5. Crime by legislative district (ESTIMATE)
`crime_by_legislative_district_ESTIMATE.csv` takes each year's own-report beat counts (2017–2025) × shares, by layer and weight (`pop_share_or_area_if_pop_lt50` recommended, plus `area_share`).
- Totals reconcile with the beat sums for every year.
- These are CRS offense counts, which run about 7–17% higher than the UCR Table 1 totals.
- They are estimates that assume crime is spread within each beat in proportion to residents (or area). That's weak for tourist and commercial beats such as Waikiki, Ala Moana and the airport.

## 6. Beat maps 2019–2025 and consistency
- **Renders:** `beat_maps/<year>/district_<n>.png` (850×1100, from 150-dpi renders).
- **No maps in some reports:** the 2017 and 2018 reports have no beat maps, and 2015/2016 have no beat tables.
- **Beat numbers:** identical, 158 beats, in every report 2017–2025.
- **Boundaries:** `beat_maps/beat_map_consistency_2019_2025.json` compares each year's traced layout with 2025 (bbox-normalised IoU).
  - District outline IoU with 2025 is 0.98–0.997 for D1–3 and D5–8 in every year. For D4 it is about 0.89 in every year.
  - Low beat-level IoUs show up in D4 and D5 for 2019–2022 and in D7 for 2020. These come from the lower-contrast teal fill and missing text labels in those years. For example, the 2024 PDF lacks text for beats x51/x61/x71, and the 2020 D7 map lacks 752–756.
  - Visual side-by-side checks of D1, D4 and D5 (2022/2023 vs 2025) show the same beat lines.
- **Conclusion:** no renumbering and no visible boundary change from 2019 to 2025, so the 2025 traced polygons are applied to all years. No per-year polygons were traced.

## Per-district beats and landmarks (2025 maps)
- **D1 Central Honolulu, 24 beats** (150–180): Downtown/Chinatown, Kakaako, Ala Moana, Makiki, Punchbowl, Pauoa, Tantalus to the Koolau crest. Landmarks: Bishop Museum, Punchbowl, HoMA, Aloha Tower, Manoa Falls Trail, Ala Moana Park shoreline.
- **D2 Wahiawa, 13 beats** (250–272): Mililani, Wahiawa, Waialua, Haleiwa, North Shore, Kaena Point to Waialee. Landmarks: H-2, north and west shoreline, Wheeler AAF, Schofield.
- **D3 Pearl City, 17 beats** (350–384): Waipahu, Pearl City, Aiea, Halawa, mauka to the Koolau ridge. Landmarks: Pearl Harbor East/Middle Loch, H-1/H-2/H-3 (H-3 enters D3 mauka), Wheeler, Byodo-In (windward).
- **D4 Kaneohe, 22 beats** (450–480): Kahuku to Waimanalo. Landmarks: windward shoreline, Kaneohe Bay, Mokapu (MCBH), H-3.
- **D5 Kalihi, 23 beats** (550–573): Kalihi, Kapalama, Moanalua, Salt Lake, airport, Hickam, Sand Island. Landmarks: HNL runways, Sand Island, Keehi Lagoon, Moanalua Fwy, H-1.
- **D6 Waikiki, 13 beats** (650–662): Waikiki peninsula and the west slope of Diamond Head. Landmarks: Ala Wai Canal, Kapiolani Park, Diamond Head crater.
- **D7 East Honolulu, 26 beats** (750–784): McCully/Moiliili, Manoa, Palolo, Kaimuki, Kahala, Aina Haina, Hawaii Kai to Makapuu. Landmarks: south shore, Koko Head, H-1/Kalanianaole Hwy.
- **D8 Waianae, 20 beats** (850–879): Ewa, Ewa Beach, Kapolei, Makakilo, Nanakuli, Waianae, Makaha. Landmarks: leeward shoreline, Barbers Point (Kalaeloa), West Loch.

Overlay feasibility was good for all 8 districts. All 158 beats were traced, and none were skipped.
