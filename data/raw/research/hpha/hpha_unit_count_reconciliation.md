# HPHA public housing unit counts and district assignment

Checked Sun Nov 15, 2026, about 5:46 PM HST.

## What HPHA publishes

https://hpha.hawaii.gov/programs-and-resources/public-housing (HTML saved at `.t2b_raw/hpha/hpha_public-housing.html`) states that HPHA manages **over 6,000 dwelling units across 85 federal and state public housing properties**, in 18 AMPs. The same page still publishes the inventory split **5,406 federal** and **864 state**.

The page embeds a Google My Maps map, mid=`17zAjNSq4QA0zL7KkHZ9-PUKp1LZTIM18` ("HPHA Locations"). The KML **was** downloadable with curl:

- https://www.google.com/maps/d/kml?mid=17zAjNSq4QA0zL7KkHZ9-PUKp1LZTIM18&forcekml=1
- Saved at `.t2b_raw/hpha/HPHALocations.kml` (255,342 bytes, 75 placemarks in folders for Oahu, Hawaiʻi, Kauaʻi, Maui, and Molokaʻi).

## Property inventory (`hpha_properties.csv`)

Parsed from the page's Webflow inventory grid (87 HTML rows, of which one is an exact duplicate of Salt Lake at 2907 Ala Ilima St. and was dropped). After that dedup: **86 rows, 85 unique property names** (Kahale Mua appears twice, once Federal / 25 units and once State, Family / 32 units). That is consistent with HPHA's "85 properties."

Unit sums in the inventory table (inventory counts used, not the My Maps description counts):

| Funding type | Inventory units | HPHA / Data Book published |
|---|---:|---:|
| Federal | 5,008 | 5,406 |
| State | 864 | 864 |
| Unspecified (`Ke Kumu 'Ekahi`, type left `--`) | 48 | — |
| All rows | 5,920 | 6,270 federal + state |

The federal inventory sum is **398 units short** of HPHA's 5,406 (or 350 short if the 48 untyped Waikoloa units are treated as federal). State units match exactly (864).

Kuhio Park campus in the inventory: Kuhio Homes 134 + Kuhio Park Terrace Lowrise 40 + Kuhio Park Terrace Towers 347 = **521 units**. The DHS Data Book FY2024 combined figure of 6,270 is described as excluding **570** Kuhio Park Terrace units, so those two "KPT" totals are not the same number either.

## Map vs inventory

75 map pins cover the 86 inventory rows by matching names (including campus-level pins for Puahala I–IV, Lanakila I–IV, Noelani I & II, Makani Kai Hale I & II, and Waimanalo Homes I & II). One inventory property, **Ke Kumu 'Ekahi**, has no pin; its coordinates were copied from the adjacent Ke Kumu 'Ekolu pin as a labeled inference. Several My Maps unit counts disagree with the inventory table (notably 'Ele'ele Homes 244 vs 24, Ko'olau Village 80 vs 24, Maili I 20 vs 30, and the Waimanalo campus pin 50 vs 19+22). The CSV uses the inventory table for `total_units` and notes the disagreements.

## District assignment

All 86 rows were assigned to a 2022 House district and a 2022 Senate district. Method (an **INFERENCE**): point-in-polygon of the My Maps WGS84 coordinates against `house_2022_wgs84.geojson` and `senate_2022_wgs84.geojson` in `/workspace/haic2026/district-map/data/boundaries/`. Grouped campus pins share one coordinate among the listed buildings. La'iola: the inventory city is Waipahu, but the map description and coordinates are in Wahiawa; districts follow the map coordinates.

## Comparison with HUD PSH

- HUD Picture of Subsidized Households, PHA **HI001**, 31DEC2025: **4,727** federal public housing units, **4,065** occupied (T2B-INF-04 occupancy 85.99%).
- The HUD tract file's statewide public-housing unit total is **4,728** (1-unit difference from the PHA file, previously noted).

The property list is better for *locating* developments in 2022 districts, but its federal unit total (5,008 itemized, or 5,406 as published by HPHA) does not match PSH, and My Maps counts are not always consistent with the inventory table. Occupied-vs-available, Kuhio Park treatment, and possible unlisted units all remain possible explanations; they are not fully reconciled.

## Recommendation

**Use HUD's 4,727 (HI001, Dec 2025) for federal public-housing district-level statistics**, and footnote HPHA's 5,406 federal / 864 state / "over 6,000" (Data Book 6,270 federal plus state) totals and this property inventory. Do not replace the existing `team2b_hud_assisted_by_*.csv` public-housing district roll-ups with inventory unit counts.
