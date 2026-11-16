# MANIFEST — hpd_crime (HAIC Know Your District)

Built 2026-11-16 00:00 HST (HST) on the Grok Bot box. Everything here is new. The full PDFs were not kept.

## Sources
- HPD Annual Reports 2017–2025 (URLs and pages in EXTRACTION_NOTES.md). Hub: https://www.honolulupd.org/information/annual-report/ . These are public records of the City & County of Honolulu. No explicit license; cite "Honolulu Police Department Annual Report <year>".
- 2017–2020 report URLs were found via the Internet Archive CDX index and fetched live from honolulupd.org.
- HPD Policy "Patrol Command Boundaries": https://www.honolulupd.org/policy/policy-patrol-command-boundaries/ (beat counts).
- Neighborhood Boards (City & County of Honolulu GIS): https://services.arcgis.com/tNJpAOha4mODLkXz/arcgis/rest/services/Neighborhood_Boards_with_Dissolved_Subdistricts/FeatureServer/0 . Used as the Oahu land mask for georeferencing only, and not redistributed.
- 2022 State House/Senate and Honolulu council districts: ../gis_districts (Hawaii Statewide GIS Program / City GIS).
- 2020 Census DHC block geography (hi2020.dhc, U.S. Census Bureau; public domain): ../census_bulk/dhc_2020.
- Google Maps basemap imagery is embedded in HPD's report maps ("MAP DATA: Google Maps"). The traced polygons are derived from HPD's beat lines and positioned using basemap features. The page renders in beat_maps/ are HPD report pages kept for reference.

## Status labels
- Beat polygons and all shares: **APPROXIMATE** (traced from report images; not official HPD GIS).
- crime_by_legislative_district_ESTIMATE.csv: **ESTIMATE**.

## Methods
See EXTRACTION_NOTES.md (tables and QA) and BEAT_GIS_METHOD.md (search, tracing, georeferencing, joins). Scripts are in scripts/.

## Source PDF sha256 (downloaded to /tmp, deleted after extraction)
```
14186c210d6e73904ce49499a9e02bc8b6337585575b917a1c6f860c55f626da  HPD-Annual-Report-2025.pdf
f751d042fd6d86a58a7935f1160d2d82ef0dd8cee8a43db90dcb9be9242f9e92  HPD2017annualreport-1.pdf
d21efa95c29bdf310e707182fd6b80d4c42a58ebdfea5a222f49fd8f84d91cce  HPD2018annualreport.pdf
02d08971b944e8006e0cf24831b539cc9a9cbf01dd8efb42fe6e3bbcd7cc99f4  HPD2019annualreport.pdf
94d5222cb46932c0481623a1b2c21d6a1f43a0c8c49dc59d1a180feb6a742b32  HPD2022annualreport.pdf
c04bbde06c9cd19e3f3dffd6878de5cbf1f751197347e193c05bda2b0ffb877b  HPD_-ANNUAL-REPORT_2020_FINAL_low-res.pdf
02e99ae9fed03aabfed5db8f54b9ade4f3968d04ad42dcdb98051d193fa0a446  HPD_-ANNUAL-REPORT_2021_FINAL.pdf
040240c6c1fa97360b12d62239e86ae4ca13146a3393d372085c3940b4e28f3d  HPD_-AR_2023_FINAL_PDF-A_REDUCED.pdf
7257d725bda80e96d56f67832ebb4bb11861563b22eea6b1d6dcbda384321e10  HPD_-AR_2024_WEB_Archive.pdf
```

## File checksums
See SHA256SUMS.txt.
